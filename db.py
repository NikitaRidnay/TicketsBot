from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base

engine = create_engine('postgresql+psycopg2://postgres:1111@localhost/postgres')

Base = declarative_base()
"""Модель базы данных для alembica."""

class Trables(Base):
    __tablename__ = "trables"

    ticket_id = Column(Integer, primary_key=True)
    description = Column(Text,nullable=False)
    op = Column(Text,nullable=False)
    contacts = Column(Text, nullable=False)
    status = Column(Boolean,nullable=False,DEFAULT=False)
    user_id = Column(BigInt,nullable=False)
    media = Column(Text,nullable=True)


