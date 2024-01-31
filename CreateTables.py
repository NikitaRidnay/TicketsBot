from sqlalchemy import create_engine, MetaData, Table, String, Integer, Column, Text, DateTime, Boolean
from datetime import datetime

"""Скрипт для создания таблицы"""

engine = create_engine("postgresql+psycopg2://postgres:1111@localhost/test", echo=True)
engine.connect()

metadata = MetaData()

Tickets = Table('tickets', metadata,
                 Column('ticket_id', Integer, primary_key=True,unique=True,index=True),
                 Column('description', Text, nullable=False),
                 Column('op',Text,nullable=False),
                 Column('contacts',Text,nullable=False),
                 Column('status', Boolean, default=False),
                 Column('user_id', Bigint,nullable=False),
                 Column('media', text, nullable=True))

metadata.create_all(engine)


