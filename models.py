from sqlalchemy import Column, Integer, String, Text
from pgvector.sqlalchemy import Vector
from database import Base

class PDFChunk(Base):

    __tablename__ = "pdf_chunks"

    id = Column(Integer, primary_key=True)
    file_name = Column(String)
    chunk_text = Column(Text)
    embedding = Column(Vector(384))