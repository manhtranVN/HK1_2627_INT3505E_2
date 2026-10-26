import sqlite3
import json
from datetime import datetime, timezone
from config import Config

def get_db_connection(db_path=None):
    if db_path is None:
        db_path = Config.DATABASE_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        avatar_url TEXT,
        role TEXT NOT NULL DEFAULT 'user',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL REFERENCES users(id),
        content TEXT NOT NULL,
        media_urls TEXT DEFAULT '[]',
        visibility TEXT NOT NULL CHECK(visibility IN ('public', 'friends_only', 'private')) DEFAULT 'public',
        tags TEXT DEFAULT '[]',
        likes_count INTEGER DEFAULT 0,
        comments_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS friendships (
        user_id INTEGER NOT NULL REFERENCES users(id),
        friend_id INTEGER NOT NULL REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, friend_id)
    );

    CREATE TABLE IF NOT EXISTS revoked_tokens (
        jti TEXT PRIMARY KEY,
        revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

def find_user_by_email(email, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def find_user_by_id(user_id, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_post_with_author(post_id, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.author_id, p.content, p.media_urls, p.visibility, p.tags,
               p.likes_count, p.comments_count, p.created_at, p.updated_at,
               u.username as author_username, u.full_name as author_full_name, u.avatar_url as author_avatar_url
        FROM posts p
        JOIN users u ON p.author_id = u.id
        WHERE p.id = ?
    """, (post_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    
    row_dict = dict(row)
    return {
        "id": row_dict["id"],
        "author": {
            "id": row_dict["author_id"],
            "username": row_dict["author_username"],
            "full_name": row_dict["author_full_name"],
            "avatar_url": row_dict["author_avatar_url"]
        },
        "content": row_dict["content"],
        "media_urls": json.loads(row_dict["media_urls"]) if row_dict["media_urls"] else [],
        "visibility": row_dict["visibility"],
        "tags": json.loads(row_dict["tags"]) if row_dict["tags"] else [],
        "likes_count": row_dict["likes_count"],
        "comments_count": row_dict["comments_count"],
        "created_at": row_dict["created_at"],
        "updated_at": row_dict["updated_at"]
    }

def are_friends(user_id_1, user_id_2, db_path=None):
    if user_id_1 == user_id_2:
        return True
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM friendships 
        WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
    """, (user_id_1, user_id_2, user_id_2, user_id_1))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def revoke_token(jti, expires_at=None, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)", (jti, expires_at))
    conn.commit()
    conn.close()

def is_token_revoked(jti, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM revoked_tokens WHERE jti = ?", (jti,))
    row = cursor.fetchone()
    conn.close()
    return row is not None
