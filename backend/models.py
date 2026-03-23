from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)  # Supabase Auth UUID
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    persona = Column(String)  # Student, Investor, Founder, etc.
    preferred_language = Column(String, default='English')

class Article(Base):
    __tablename__ = 'articles'

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content_summary = Column(Text)
    original_url = Column(String, unique=True, nullable=False)
    published_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    embedding_id = Column(String)  # Link to vector DB
