from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from pgvector.sqlalchemy import Vector
from database import Base

class PDFChunk(Base):

    __tablename__ = "pdf_chunks"

    id = Column(Integer, primary_key=True)
    file_name = Column(String)
    candidate_name = Column(String)
    chunk_text = Column(Text)
    embedding = Column(Vector(384))

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    file_name = Column(String)
    name = Column(String)

    skills = Column(JSON, nullable=True)
    projects = Column(JSON, nullable=True)
    experience = Column(JSON, nullable=True)
    hackathons = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)