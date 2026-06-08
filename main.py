from multiprocessing import context
from database import SessionLocal
from models import PDFChunk, Resume
from embeddings import get_embedding
from pdf_utils import extract_text_from_pdf
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from database import Base, engine
from chunking import  split_by_words
from sqlalchemy import text
from rag import ask_llm, extract_name

import chunking
import models, traceback
import shutil
import time
import multipart
import os

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

        # # Extract structured resume data
        # structured = extract_structured_resume(
        #     text
        # )

        # # Save Resume table row
        # resume_obj = Resume(
        #     file_name=file.filename,
        #     name=structured.get("name"),
        #     skills=structured.get("skills", []),
        #     projects=structured.get("projects", []),
        #     experience=structured.get("experience", []),
        #     hackathons=structured.get("hackathons", []),
        #     education=structured.get("education", [])
        # )

        # db.add(resume_obj)

        candidate_name = extract_name(text).lower()

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

# @app.get("/search")
# def search(query: str):

#     db = SessionLocal()

#     try:

#         query_lower = query.lower()

#         # SKILL LOOKUP

#         if query_lower.startswith("who knows"):

#             skill = (
#                 query_lower
#                 .replace("who knows", "")
#                 .replace("?", "")
#                 .strip()
#             )

#             resumes = db.query(Resume).all()

#             matching_people = []

#             for resume in resumes:

#                 skills = [
#                     s.lower()
#                     for s in (resume.skills or [])
#                 ]

#                 if any(skill in s for s in skills):

#                     matching_people.append(
#                         resume.name
#                     )

#             return {
#                 "skill": skill,
#                 "people": matching_people
#             }

#         # VECTOR SEARCH

#         start = time.time()

#         query_embedding = get_embedding(query)

#         print(
#             "Embedding time:",
#             time.time() - start
#         )

#         # FIND PERSON NAME IN QUERY

#         resumes = db.query(Resume).all()

#         matched_name = None

#         for resume in resumes:

#             if (
#                 resume.name
#                 and resume.name.lower()
#                 in query_lower
#             ):
#                 matched_name = resume.name
#                 break

#         # PERSON-SPECIFIC SEARCH

#         if matched_name:

#             print(
#                 "Searching only for:",
#                 matched_name
#             )

#             results = (
#                 db.query(PDFChunk)
#                 .filter(
#                     PDFChunk.candidate_name == matched_name
#                 )
#                 .order_by(
#                     PDFChunk.embedding.cosine_distance(
#                         query_embedding
#                     )
#                 )
#                 .limit(10)
#                 .all()
#             )

#         # GLOBAL SEARCH

#         else:

#             results = (
#                 db.query(PDFChunk)
#                 .order_by(
#                     PDFChunk.embedding.cosine_distance(
#                         query_embedding
#                     )
#                 )
#                 .limit(10)
#                 .all()
#             )

#         if not results:

#             return {
#                 "message":
#                 "No matching documents found"
#             }

#         # BUILD CONTEXT

#         context = "\n\n".join(
#             [
#                 f"""
# FILE: {row.file_name}

# CANDIDATE: {row.candidate_name}

# SECTION: {row.section}

# {row.chunk_text}
# """
#                 for row in results
#             ]
#         )

#         print(
#             "\n===== CONTEXT ====="
#         )

#         print(context)

#         print(
#             "\n===================\n"
#         )

#         # LLM

#         answer = ask_llm(
#             context=context,
#             question=query
#         )

#         return {
#             "answer": answer,
#             "matched_files": list(
#                 set(
#                     row.file_name
#                     for row in results
#                 )
#             )
#         }

#     except Exception as e:

#         import traceback

#         print(
#             traceback.format_exc()
#         )

#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )

#     finally:

#         db.close()


# app = FastAPI()


# @app.get("/search")
# def search(query: str):

#     db = SessionLocal()

#     try:
#         query_lower = query.lower().strip()

#         start = time.time()
#         query_embedding = get_embedding(query)
#         print("Embedding time:", time.time() - start)

#         # ======================================================
#         # STEP 1: CHECK IF QUERY CONTAINS A PERSON NAME
#         # ======================================================
#         candidate_names = (
#             db.query(PDFChunk.candidate_name)
#             .distinct()
#             .all()
#         )

#         matched_name = None

#         for row in candidate_names:
#             if row[0] and row[0].lower() in query_lower:
#                 matched_name = row[0]
#                 break

#         # ======================================================
#         # STEP 2: PERSON-SPECIFIC SEARCH (MOST IMPORTANT)
#         # ======================================================
#         if matched_name:

#             print("Searching resume for:", matched_name)

#             results = (
#                 db.query(PDFChunk)
#                 .filter(PDFChunk.candidate_name == matched_name)
#                 .all()
#             )

#             if not results:
#                 return {
#                     "message": "No data found for this candidate"
#                 }

#             # build full resume context
#             context = "\n\n".join(
#                 r.chunk_text for r in results
#             )

#             print("\n===== CONTEXT (PERSON) =====")
#             print(context[:3000])
#             print("============================\n")

#             answer = ask_llm(
#                 context=context,
#                 question=query
#             )

#             return {
#                 "answer": answer,
#                 "matched_files": list(set(r.file_name for r in results)),
#                 "matched_name": matched_name
#             }

#         # ======================================================
#         # STEP 3: GENERAL SEARCH (NO PERSON NAME FOUND)
#         # ======================================================
#         top_chunks = (
#             db.query(PDFChunk)
#             .order_by(
#                 PDFChunk.embedding.cosine_distance(query_embedding)
#             )
#             .limit(50)   # IMPORTANT: increased from 10
#             .all()
#         )

#         if not top_chunks:
#             return {
#                 "message": "No matching documents found"
#             }

#         # pick best PDF based on chunk votes
#         from collections import Counter

#         pdf_counter = Counter(
#             chunk.file_name
#             for chunk in top_chunks
#             if chunk.file_name
#         )

#         best_pdf = pdf_counter.most_common(1)[0][0]

#         print("Best matching PDF:", best_pdf)

#         # load full document of that PDF
#         results = (
#             db.query(PDFChunk)
#             .filter(PDFChunk.file_name == best_pdf)
#             .all()
#         )

#         if not results:
#             return {
#                 "message": "No matching documents found"
#             }

#         # build full context
#         context = "\n\n".join(
#             r.chunk_text for r in results
#         )

#         print("\n===== CONTEXT (GENERAL) =====")
#         print(context[:3000])
#         print("============================\n")

#         answer = ask_llm(
#             context=context,
#             question=query
#         )

#         return {
#             "answer": answer,
#             "matched_files": list(set(r.file_name for r in results))
#         }

#     except Exception as e:
#         import traceback
#         print(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         db.close()
import difflib

@app.get("/search")
def search(query: str):

    db = SessionLocal()

    try:
        query_lower = query.lower().strip()
        # Strip possessives before anything
        query_clean = query_lower.replace("'s", "").replace("\u2019s", "")
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
                "answer": answer,
                "matched_name": matched_name,
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
            "answer": answer,
            "matched_candidates": matched_candidates,
            "matched_files": list(set(r.file_name for r in relevant_chunks))
        }

    finally:
        db.close()