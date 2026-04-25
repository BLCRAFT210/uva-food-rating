from contextlib import contextmanager

import pymysql
from flask import current_app, g
from pymysql.cursors import DictCursor


def get_db():
    if "db" not in g:
        g.db = pymysql.connect(
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"],
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
        )
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def query_all(sql, params=None):
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()


def query_one(sql, params=None):
    rows = query_all(sql, params)
    if rows:
        return rows[0]
    return None


def execute(sql, params=None):
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute(sql, params or ())
        conn.commit()
        return cursor.rowcount


def execute_and_get_id(sql, params=None):
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute(sql, params or ())
        new_id = cursor.lastrowid
        conn.commit()
        return new_id


@contextmanager
def transaction():
    conn = get_db()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
