from sqlalchemy import create_engine

"""Скрипт для подключения SqlAlchemy."""

engine = create_engine("postgresql+psycopg2://postgres:1111@localhost/test", echo=True)
engine.connect()

print(engine)