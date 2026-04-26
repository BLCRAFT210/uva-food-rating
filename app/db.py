from contextlib import contextmanager

import pymysql
from flask import current_app, g
from pymysql.cursors import DictCursor
from google.cloud.sql.connector import Connector


# Initialize Cloud SQL Connector
connector = Connector()


def get_db():
    if "db" not in g:
        if current_app.config.get("INSTANCE_CONNECTION_NAME"):
            # Connect using Cloud SQL Connector
            # Note: We set autocommit and cursorclass on the connection object/cursors
            # as the connector's connect() method primary job is the secure tunnel.
            g.db = connector.connect(
                current_app.config["INSTANCE_CONNECTION_NAME"],
                "pymysql",
                user=current_app.config["DB_USER"],
                password=current_app.config["DB_PASSWORD"],
                db=current_app.config["DB_NAME"],
                charset="utf8mb4",
            )
            # Set PyMySQL specific attributes
            g.db.autocommit(False)
            g.db.cursorclass = DictCursor
        else:
            # Connect using standard PyMySQL (for local dev or direct IP)
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
