import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from config import Config
import database
from auth import hash_password

def seed_database(db_path=None):
    if db_path is None:
        db_path = Config.DATABASE_PATH
        
    print(f"[*] Initializing database schema at: {db_path}")
    database.init_db(db_path)
    
    conn = database.get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Xóa dữ liệu cũ nếu có
    cursor.execute("DELETE FROM revoked_tokens")
    cursor.execute("DELETE FROM friendships")
    cursor.execute("DELETE FROM posts")
    cursor.execute("DELETE FROM users")
    
    print("[*] Hashing passwords with Argon2id...")
    alice_hash = hash_password("AliceSecurePass123!")
    bob_hash = hash_password("BobSecurePass123!")
    charlie_hash = hash_password("CharliePass123!")
    admin_hash = hash_password("AdminSecretPass2026!")
    
    print("[*] Inserting sample users...")
    cursor.execute("""
        INSERT INTO users (id, username, email, password_hash, full_name, avatar_url, role)
        VALUES 
        (1, 'alice', 'alice@example.com', ?, 'Alice Nguyen', 'https://avatar.socialnetwork.example.com/alice.png', 'user'),
        (2, 'bob', 'bob@example.com', ?, 'Bob Tran', 'https://avatar.socialnetwork.example.com/bob.png', 'user'),
        (3, 'charlie', 'charlie@example.com', ?, 'Charlie Le', 'https://avatar.socialnetwork.example.com/charlie.png', 'user'),
        (4, 'admin', 'admin@example.com', ?, 'Admin Master', 'https://avatar.socialnetwork.example.com/admin.png', 'admin')
    """, (alice_hash, bob_hash, charlie_hash, admin_hash))
    
    print("[*] Inserting friendships (Alice & Bob are friends; Charlie is stranger)...")
    cursor.execute("""
        INSERT INTO friendships (user_id, friend_id)
        VALUES (1, 2)
    """)
    
    print("[*] Inserting sample posts with different visibilities (public, friends_only, private)...")
    cursor.execute("""
        INSERT INTO posts (id, author_id, content, media_urls, visibility, tags, likes_count, comments_count)
        VALUES
        (101, 1, 'Hôm nay tôi hoàn thành bài lab bảo mật API về JWT và RBAC! #learning #security', 
         ?, 'public', ?, 42, 7),
        (102, 1, 'Cập nhật bài viết chia sẻ ảnh gia đình - chỉ dành riêng cho bạn bè của Alice!', 
         ?, 'friends_only', ?, 18, 3),
        (103, 1, 'Nhật ký cá nhân tuyệt mật của Alice - chỉ Alice hoặc Quản trị viên mới được xem!', 
         ?, 'private', ?, 0, 0),
        (104, 2, 'Chào mọi người, tôi là Bob! Đang học môn Kiến trúc hướng dịch vụ UET.', 
         ?, 'public', ?, 15, 2)
    """, (
        json.dumps(["https://cdn.socialnetwork.example.com/photos/post-101.jpg"]),
        json.dumps(["learning", "security"]),
        json.dumps(["https://cdn.socialnetwork.example.com/photos/family.jpg"]),
        json.dumps(["friends", "family"]),
        json.dumps([]),
        json.dumps(["diary", "secret"]),
        json.dumps([]),
        json.dumps(["uet", "hello"])
    ))
    
    conn.commit()
    conn.close()
    print("[+] Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
