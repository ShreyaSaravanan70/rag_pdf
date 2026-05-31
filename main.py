from database import SessionLocal
from models import PDFChunk
from embeddings import get_embedding
from pdf_utils import extract_text_from_pdf
from fastapi import FastAPI, UploadFile, File, Request
from database import Base, engine
from rag import ask_llm
import models
import shutil
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

    # create embedding
    embedding = get_embedding(text)

    # create row
    pdf_chunk = PDFChunk(
        file_name=file.filename,
        chunk_text=text,
        embedding=embedding
    )

    # save to database
    db.add(pdf_chunk)

    db.commit()

    return {
        "message": "PDF stored successfully"
    }

@app.get("/search")
def search(query: str):

    db = SessionLocal()

    # Convert question to embedding
    query_embedding = get_embedding(query)

    # Get top 3 most similar documents
    results = (
        db.query(PDFChunk)
        .order_by(
            PDFChunk.embedding.cosine_distance(query_embedding)
        )
        .limit(3)
        .all()
    )

    if not results:
        return {
            "message": "No matching documents found"
        }

    # Debug: see what was retrieved
    print("\nTop Matches:")
    for r in results:
        print(r.file_name)

    # Combine contexts
    context = "\n\n".join(
        [
            f"FILE: {r.file_name}\n{r.chunk_text}"
            for r in results
        ]
    )

    answer = ask_llm(
        context=context,
        question=query
    )

    return {
        "answer": answer,
        "matched_files": [
            r.file_name
            for r in results
        ]
    }