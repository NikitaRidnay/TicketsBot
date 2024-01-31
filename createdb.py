import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

"""Скрипт для создания базы данных."""

connection = psycopg2.connect(user="postgres", password="1111")
connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

cursor = connection.cursor()
sql_create_database = cursor.execute('create database test')

cursor.close()
connection.close()