from multiprocessing import context

from database import SessionLocal
from models import PDFChunk
from embeddings import get_embedding
from pdf_utils import extract_text_from_pdf
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from database import Base, engine
from sqlalchemy import text
from rag import ask_llm
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

    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    # extract text
    text = extract_text_from_pdf(
        file_path
    )
    
    chunks = chunking.split_by_chars(text, chunk_size=1000, overlap=200)

    print("Total chunks:", len(chunks))  # debug (optional)

    # 3. store each chunk
    for chunk in chunks:

        embedding = get_embedding(chunk)

        pdf_chunk = PDFChunk(
            file_name=file.filename,
            chunk_text=chunk,
            embedding=embedding
        )

        db.add(pdf_chunk)

    db.commit()
    db.close()

    return {
        "message": "PDF stored successfully",
        "total_chunks": len(chunks)
    }

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
from fastapi import HTTPException
from sqlalchemy import text
import time

@app.get("/search")
def search(query: str):

    db = SessionLocal()

    try:

        # 1. Generate query embedding
        start = time.time()

        query_embedding = get_embedding(query)

        print("Embedding time:", time.time() - start)

        # 2. Hierarchical retrieval
        start = time.time()

        results = db.execute(
            text("""
                WITH chunk_scores AS (
                    SELECT
                        file_name,
                        chunk_text,
                        embedding <=> CAST(:embedding AS vector) AS distance
                    FROM pdf_chunks
                ),

                ranked_chunks AS (
                    SELECT
                        file_name,
                        chunk_text,
                        distance,
                        ROW_NUMBER() OVER (
                            PARTITION BY file_name
                            ORDER BY distance ASC
                        ) AS rn
                    FROM chunk_scores
                ),

                top_files AS (
                    SELECT
                        file_name,
                        MIN(distance) AS best_distance
                    FROM chunk_scores
                    GROUP BY file_name
                    ORDER BY best_distance ASC
                    LIMIT :limit_docs
                )

                SELECT
                    rc.file_name,
                    rc.chunk_text,
                    rc.distance
                FROM ranked_chunks rc
                JOIN top_files tf
                    ON rc.file_name = tf.file_name
                WHERE rc.rn <= :top_chunks_per_doc
                ORDER BY
                    tf.best_distance ASC,
                    rc.file_name,
                    rc.distance ASC
            """),
            {
                "embedding": str(query_embedding),
                "limit_docs": 5,
                "top_chunks_per_doc": 3
            }
        ).fetchall()

        print("Search time:", time.time() - start)

        if not results:
            return {
                "message": "No matching documents found"
            }

        # 3. Build context
        context = "\n\n".join(
            [
                f"FILE: {row.file_name}\n{row.chunk_text}"
                for row in results
            ]
        )

        # 4. Ask LLM
        start = time.time()

        print("\n===== RETRIEVED CHUNKS =====")

        for row in results:
            print("\nFILE:", row.file_name)
            print(row.chunk_text[:1000])

        print("\n============================")

        # answer = ask_llm(
        #     context=context,
        #     question=query
        # )
        return {
            "context": context,
            "matched_files": list(set(row.file_name for row in results))
        }

        print("LLM time:", time.time() - start)

        # return {
        #     "answer": answer,
        #     "matched_files": list(
        #         set(row.file_name for row in results)
        #     )
        # }

    except Exception as e:
        import traceback
        print(traceback.format_exc())

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()