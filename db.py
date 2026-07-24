import sqlite3
import os
from flask import g

DATABASE = 'guardian.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY,
      username TEXT UNIQUE,
      password_hash TEXT,
      role TEXT CHECK(role IN ('kid','guardian')),
      guardian_email TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY,
      sender_id INTEGER,
      receiver_id INTEGER,
      text TEXT,
      severity TEXT CHECK(severity IN ('safe','flagged','high')),
      is_bullying BOOLEAN,
      reason TEXT,
      timestamp TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
      id INTEGER PRIMARY KEY,
      message_id INTEGER,
      confidence INTEGER,
      status TEXT DEFAULT 'new',
      timestamp TEXT
    )
    ''')
    conn.commit()
    conn.close()

if not os.path.exists(DATABASE):
    init_db()
