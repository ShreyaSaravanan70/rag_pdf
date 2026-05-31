import os

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# load variables from .env
load_dotenv()

# get database url from .env
DATABASE_URL = os.getenv("DATABASE_URL")

# create database engine
engine = create_engine(DATABASE_URL)

# create session
SessionLocal = sessionmaker(
    bind=engine
)

# base class for models
Base = declarative_base()