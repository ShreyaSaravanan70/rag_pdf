from multiprocessing import context
from database import SessionLocal
from models import PDFChunk, Resume
from embeddings import get_embedding
from pdf_utils import extract_text_from_pdf
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from database import Base, engine
from chunking import  split_by_words
from sqlalchemy import text
from rag import ask_llm, extract_structured_resume
import difflib
import chunking
import models, traceback
import shutil
import time
import multipart
import os
import re

app=FastAPI(title="This is a PDF Rag Project")

Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "PDF RAG System Running"}   
@app.post("/upload_pdf")
def upload_pdf(
    file: UploadFile = File(...)
):

    db = SessionLocal()

    try:

        file_path = f"uploads/{file.filename}"

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        # Extract text
        text = extract_text_from_pdf(
            file_path
        )


        # Extract structured resume data
        structured = extract_structured_resume(text)

        candidate_name = structured.get("name", "").strip()

        # Save Resume table row
        resume_obj = Resume(
            file_name=file.filename,
            name=candidate_name,
            skills=structured.get("skills", []),
            projects=structured.get("projects", []),
            experience=structured.get("experience", []),
            hackathons=structured.get("hackathons", []),
            education=structured.get("education", [])
        )

        db.add(resume_obj)


        # word-based chunks
        chunks = split_by_words(
            text,
            chunk_size=150,
            overlap=30
        )

        print("Total chunks:", len(chunks))
    

        # Store chunks
        for chunk in chunks:

            embedding = get_embedding(
                chunk["content"]
            )

            pdf_chunk = PDFChunk(
                file_name=file.filename,

                candidate_name=candidate_name,


                chunk_text=chunk["content"],

                embedding=embedding
            )

            db.add(pdf_chunk)

        db.commit()

        return {
            "message": "PDF stored successfully",
            "candidate_name": candidate_name,
            "total_chunks": len(chunks)
        }

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        print("ERROR:", str(e))
        raise e

    finally:
        db.close()


@app.get("/search")
def search(query: str):

    db = SessionLocal()

    try:
        # all_names = (
        #     db.query(PDFChunk.candidate_name)
        #     .distinct()
        #     .all()
        # )

        # return {
        #     "all_names": [n[0] for n in all_names]
        # }
    
        query_lower = query.lower().strip()
            # Remove possessive 's and curly apostrophe ’s
        query_clean = (
            query_lower
            .replace("'s", "")
            .replace("\u2019s", "")
        )

        # Remove all punctuation
        query_clean = re.sub(
            r"[^\w\s]",
            " ",
            query_clean
        )

        # Remove extra spaces
        query_clean = " ".join(query_clean.split())
        query_embedding = get_embedding(query)

        STOPWORDS = {
            "what", "who", "is", "the", "a", "an", "about", "does", "do",
            "has", "have", "tell", "me", "show", "find", "his", "her",
            "their", "resume", "profile", "candidate", "experience", "skills",
            "background", "work", "for", "with", "and", "or", "of", "in", "on",
            "all", "knows", "know", "which", "are", "can", "list"
        }

        # ======================================================
        # LOAD NAMES
        # ======================================================
        candidate_rows = (
            db.query(PDFChunk.candidate_name)
            .distinct()
            .all()
        )

        names = [r[0] for r in candidate_rows if r[0]]

        # ======================================================
        # INLINE NAME MATCHER (STRICT)
        # ======================================================
        matched_name = None

        query_tokens = [
            t for t in query_clean.split()
            if t not in STOPWORDS and len(t) >= 3
        ]

        for name in names:
            if not name:
                continue

            name_lower = name.lower().strip()

            # exact match
            if name_lower == query_clean:
                matched_name = name
                break

            # full name inside cleaned query
            if name_lower in query_clean:
                matched_name = name
                break

            # all name tokens must exist in query tokens
            name_tokens = [
                t for t in name_lower.split()
                if t not in STOPWORDS and len(t) >= 3
            ]

            if name_tokens and all(t in query_tokens for t in name_tokens):
                matched_name = name
                break

            # fuzzy fallback — every name token must match at ratio >= 0.80
            if name_tokens and query_tokens:
                fuzzy_hits = sum(
                    1 for nt in name_tokens
                    if difflib.get_close_matches(nt, query_tokens, n=1, cutoff=0.80)
                )
                if fuzzy_hits == len(name_tokens):
                    matched_name = name
                    break

        # ======================================================
        # PERSON QUERY → STRICT RESUME LOCK
        # ======================================================
        if matched_name:

            print("Matched candidate:", matched_name)

            # Check if this person actually exists in DB (lowercase compare)
            results = (
                db.query(PDFChunk)
                .filter(PDFChunk.candidate_name.ilike(matched_name))
                .all()
            )

            if not results:
                return {"answer": f"No resume found for '{matched_name}'."}

            # Feed only this candidate's chunks to LLM
            context = "\n\n".join(r.chunk_text for r in results)

            answer = ask_llm(
                context=context,
                question=query
            )

            return {
                 "type": "person_query",
                "answer": answer,
                "matched_files": list(set(r.file_name for r in results))
            }

        # ======================================================
        # "WHO ALL KNOWS / HAS" → SEMANTIC SEARCH ACROSS ALL
        # ======================================================
        top_chunks = (
            db.query(PDFChunk)
            .order_by(
                PDFChunk.embedding.cosine_distance(query_embedding)
            )
            .limit(20)
            .all()
        )

        if not top_chunks:
            return {"message": "No matching documents found"}

        # Filter only chunks where the skill/topic actually appears in the text
        keyword_tokens = [
            t for t in query_clean.split()
            if t not in STOPWORDS and len(t) >= 3
        ]

        relevant_chunks = [
            chunk for chunk in top_chunks
            if any(token in chunk.chunk_text.lower() for token in keyword_tokens)
        ]

        if not relevant_chunks:
            return {"message": "No candidates found with the requested skill or experience"}

        # Extract unique candidate names from relevant chunks
        matched_candidates = list(set(
            chunk.candidate_name for chunk in relevant_chunks
            if chunk.candidate_name
        ))

        context = "\n\n".join(r.chunk_text for r in relevant_chunks)

        print("CONTEXT PREVIEW:", context[:500])
        print("CHUNK COUNT:", len(relevant_chunks))  

        answer = ask_llm(
            context=context,
            question=query
        )

        return {
            "type": "skill_query",
            "matched_candidates": matched_candidates,
            "matched_files": list(set(r.file_name for r in relevant_chunks))
        }

    finally:
        db.close()