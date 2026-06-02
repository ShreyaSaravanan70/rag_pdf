from multiprocessing import context
from database import SessionLocal
from models import PDFChunk, Resume
from embeddings import get_embedding
from pdf_utils import extract_text_from_pdf
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from database import Base, engine
from chunking import split_by_headings
from sqlalchemy import text
from rag import ask_llm, extract_structured_resume
import chunking
import models
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

        # Extract structured resume data
        structured = extract_structured_resume(
            text
        )

        # Save Resume table row
        resume_obj = Resume(
            file_name=file.filename,
            name=structured.get("name"),
            skills=structured.get("skills", []),
            projects=structured.get("projects", []),
            experience=structured.get("experience", []),
            hackathons=structured.get("hackathons", []),
            education=structured.get("education", [])
        )

        db.add(resume_obj)

        # Heading-based chunks
        chunks = chunking.split_by_headings(text)

        print("Total chunks:", len(chunks))

        # Store chunks
        for chunk in chunks:

            embedding = get_embedding(
                chunk["content"]
            )

            pdf_chunk = PDFChunk(
                file_name=file.filename,

                candidate_name=structured.get(
                    "name",
                    ""
                ),

                section=chunk["section"],

                chunk_text=chunk["content"],

                embedding=embedding
            )

            db.add(pdf_chunk)

        db.commit()

        return {
            "message": "PDF stored successfully",
            "candidate_name": structured.get("name"),
            "total_chunks": len(chunks)
        }

    except Exception as e:
        db.rollback()
        raise e

    finally:
        db.close()

# @app.get("/search")
# def search(query: str):

#     db = SessionLocal()

#     try:
#         # 1. Get embedding
#         query_embedding = get_embedding(query)

#         # 2. Run query safely using SQLAlchemy
#         results = db.execute(
#             text("""
#                 WITH chunk_scores AS (
#                     SELECT
#                         file_name,
#                         chunk_text,
#                         embedding <=> CAST(:embedding AS vector) AS distance
#                     FROM pdf_chunks
#                 ),

#                 ranked_chunks AS (
#                     SELECT
#                         file_name,
#                         chunk_text,
#                         distance,
#                         ROW_NUMBER() OVER (
#                             PARTITION BY file_name
#                             ORDER BY distance ASC
#                         )   AS rn
#                     FROM chunk_scores
#                 ),

#                 top_files AS (
#                     SELECT
#                         file_name,
#                         MIN(distance) AS best_distance
#                     FROM chunk_scores
#                     GROUP BY file_name
#                     ORDER BY best_distance ASC
#                     LIMIT :limit_docs
#             )

#                 SELECT
#                     rc.file_name,
#                     rc.chunk_text,
#                     rc.distance
#                 FROM ranked_chunks rc
#                 JOIN top_files tf
#                     ON rc.file_name = tf.file_name
#                 WHERE rc.rn <= :top_chunks_per_doc
#                 ORDER BY 
#                     tf.best_distance ASC,
#                     rc.file_name,
#                     rc.distance ASC
#             """),
#             {
#                 "embedding": str(query_embedding),
#                 "limit_docs": 5,
#                 "top_chunks_per_doc": 3
#             }
#         ).fetchall()

#         if not results:
#             return {"message": "No matching documents found"}

#         # 3. Build context
#         context = "\n\n".join(
#             f"FILE: {r.file_name}\n{r.chunk_text}"
#             for r in results
#         )

#         # 4. LLM call
#         answer = ask_llm(context=context, question=query)

#         return {
#             "answer": answer,
#             "matched_files": list(set(r.file_name for r in results))
#         }

#     except Exception as e:
#         print("ERROR:", e)   # 🔥 IMPORTANT DEBUG LINE
#         raise e

#     finally:
#         db.close()
@app.get("/search")
def search(query: str):

    db = SessionLocal()

    try:

        query_lower = query.lower()

        # =====================================
        # SKILL LOOKUP
        # =====================================

        if query_lower.startswith("who knows"):

            skill = (
                query_lower
                .replace("who knows", "")
                .replace("?", "")
                .strip()
            )

            resumes = db.query(Resume).all()

            matching_people = []

            for resume in resumes:

                skills = [
                    s.lower()
                    for s in (resume.skills or [])
                ]

                if any(skill in s for s in skills):

                    matching_people.append(
                        resume.name
                    )

            return {
                "skill": skill,
                "people": matching_people
            }

        # =====================================
        # VECTOR SEARCH
        # =====================================

        start = time.time()

        query_embedding = get_embedding(query)

        print(
            "Embedding time:",
            time.time() - start
        )

        # =====================================
        # FIND PERSON NAME IN QUERY
        # =====================================

        resumes = db.query(Resume).all()

        matched_name = None

        for resume in resumes:

            if (
                resume.name
                and resume.name.lower()
                in query_lower
            ):
                matched_name = resume.name
                break

        # =====================================
        # PERSON-SPECIFIC SEARCH
        # =====================================

        if matched_name:

            print(
                "Searching only for:",
                matched_name
            )

            results = (
                db.query(PDFChunk)
                .filter(
                    PDFChunk.candidate_name
                    == matched_name
                )
                .order_by(
                    PDFChunk.embedding.cosine_distance(
                        query_embedding
                    )
                )
                .limit(10)
                .all()
            )

        # =====================================
        # GLOBAL SEARCH
        # =====================================

        else:

            results = (
                db.query(PDFChunk)
                .order_by(
                    PDFChunk.embedding.cosine_distance(
                        query_embedding
                    )
                )
                .limit(10)
                .all()
            )

        if not results:

            return {
                "message":
                "No matching documents found"
            }

        # =====================================
        # BUILD CONTEXT
        # =====================================

        context = "\n\n".join(
            [
                f"""
FILE: {row.file_name}

CANDIDATE: {row.candidate_name}

SECTION: {row.section}

{row.chunk_text}
"""
                for row in results
            ]
        )

        print(
            "\n===== CONTEXT ====="
        )

        print(context)

        print(
            "\n===================\n"
        )

        # =====================================
        # LLM
        # =====================================

        answer = ask_llm(
            context=context,
            question=query
        )

        return {
            "answer": answer,
            "matched_files": list(
                set(
                    row.file_name
                    for row in results
                )
            )
        }

    except Exception as e:

        import traceback

        print(
            traceback.format_exc()
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()