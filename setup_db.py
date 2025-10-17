# setup_db.py

import sqlite3

conn = sqlite3.connect('mcp_database.db')
cursor = conn.cursor()

# Create the 'files' table (no changes here)
cursor.execute('''
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL
)
''')

# NEW: Create a 'conversations' table to group chats by topic
cursor.execute('''
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# UPDATED: 'chat_history' is now linked to a conversation_id
cursor.execute('''
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender TEXT NOT NULL, -- 'user' or 'ai'
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
)
''')

conn.commit()
conn.close()

print("✅ Database and tables ('files', 'conversations', 'chat_history') created successfully.")