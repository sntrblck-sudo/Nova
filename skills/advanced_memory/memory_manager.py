import sqlite3
import sys
import os
from datetime import datetime

DB_PATH = '/home/sntrblck/.openclaw/workspace/memory/nova_memory.db'
MD_PATH = '/home/sntrblck/.openclaw/workspace/MEMORY.md'

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS memories
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    tags TEXT,
    content TEXT)''')
    return conn

def remember(tags, content):
    conn = get_connection()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Insert into SQLite
    conn.execute("INSERT INTO memories (timestamp, tags, content) VALUES (?, ?, ?)", 
                 (timestamp, tags, content))
    conn.commit()
    conn.close()
    
    # Append to legacy MEMORY.md
    try:
        with open(MD_PATH, 'a') as f:
            f.write(f"\n- [{timestamp}] [{tags}] {content}")
        print(f"Memory saved and appended to MEMORY.md.")
    except Exception as e:
        print(f"Saved to DB, but failed to update MEMORY.md: {e}")

def recall(query):
    conn = get_connection()
    cursor = conn.cursor()
    # Search in both tags and content
    cursor.execute("SELECT id, timestamp, tags, content FROM memories WHERE tags LIKE ? OR content LIKE ?", 
                   (f"%{query}%", f"%{query}%"))
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        print("No memories found matching that query.")
        return
    
    for row in results:
        print(f"ID: {row[0]} | Time: {row[1]} | Tags: {row[2]}\nContent: {row[3]}\n-")

def heartbeat(since_timestamp):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, tags, content FROM memories WHERE timestamp >= ? ORDER BY timestamp ASC", 
                   (since_timestamp,))
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        print("No new memories since " + since_timestamp)
        return
    
    print(f"--- Changes since {since_timestamp} ---")
    for row in results:
        print(f"[{row[1]}] ({row[2]}): {row[3]}")

def forget(memory_id):
    conn = get_connection()
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    deleted = conn.total_changes
    conn.close()
    
    if deleted > 0:
        print(f"Memory ID {memory_id} has been forgotten. (Note: MEMORY.md was not altered).")
    else:
        print(f"Memory ID {memory_id} not found.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 memory_manager.py <command> [args]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "remember" and len(sys.argv) >= 4:
        remember(sys.argv[2], sys.argv[3])
    elif command == "recall" and len(sys.argv) >= 3:
        recall(sys.argv[2])
    elif command == "heartbeat" and len(sys.argv) >= 3:
        heartbeat(sys.argv[2])
    elif command == "forget" and len(sys.argv) >= 3:
        forget(sys.argv[2])
    else:
        print("Invalid command or missing arguments.")