import psycopg
from config import POSTGRES

def connect():
    return psycopg.connect(**POSTGRES)


def executemany(conn, query, params):
    """Execute a batch using a Psycopg 3 cursor (Connection has no executemany)."""
    with conn.cursor() as cursor:
        return cursor.executemany(query, params)
