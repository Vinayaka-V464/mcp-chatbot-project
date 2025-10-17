# app.py
# Integrated General Chat & Topic-Based History

import os
import sqlite3
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template, g
import fitz

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
DATABASE = 'mcp_database.db'
API_KEY = 'AIzaSyCtkTDavh5kVYHvklLRxxj3f56DpWGsP8o'
genai.configure(api_key=API_KEY)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Database ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Text Extraction ---
def extract_text(filepath):
    # (No changes to this function)
    if filepath.lower().endswith('.pdf'):
        try:
            doc = fitz.open(filepath)
            text = "".join(page.get_text() for page in doc)
            doc.close()
            return text
        except Exception as e:
            print(f"Error processing PDF {filepath}: {e}")
            return None
    elif filepath.lower().endswith('.txt'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error processing TXT {filepath}: {e}")
            return None
    return ""

# --- Core Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

# --- File Management Routes ---
@app.route('/sync-files', methods=['POST'])
def sync_files():
    # (No changes to this function)
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT filename FROM files")
        db_files = {row['filename'] for row in cursor.fetchall()}
        disk_files = set(os.listdir(app.config['UPLOAD_FOLDER']))
        new_files = disk_files - db_files
        
        if not new_files:
            return jsonify({'success': True, 'message': 'No new files found.'})

        processed_files = []
        for filename in new_files:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if filename.lower().endswith(('.txt', '.pdf')):
                text_content = extract_text(filepath)
                if text_content:
                    cursor.execute("INSERT OR REPLACE INTO files (filename, content) VALUES (?, ?)", (filename, text_content))
                    processed_files.append(filename)
        db.commit()
        return jsonify({'success': True, 'message': f'Synced {len(processed_files)} new file(s).', 'new_files': processed_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/files', methods=['GET'])
def get_files():
    # (No changes to this function)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT filename FROM files")
    files = [row['filename'] for row in cursor.fetchall()]
    return jsonify(files)

@app.route('/context/<filename>', methods=['GET'])
def get_context(filename):
    # (No changes to this function)
    db = get_db()
    row = db.execute("SELECT content FROM files WHERE filename = ?", (filename,)).fetchone()
    if row:
        return jsonify({'filename': filename, 'content': row['content']})
    return jsonify({'error': 'File not found'}), 404
    
@app.route('/select-file', methods=['POST'])
def select_file_with_ai():
    # (No changes to this function)
    data = request.json
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"From this list of files: {', '.join(data.get('filenames'))}, which one is the user asking for with this query: '{data.get('query')}'? Respond with only the single, exact filename."
    try:
        response = model.generate_content(prompt)
        selected_file = response.text.strip()
        if selected_file in data.get('filenames'):
            return jsonify({'selected_file': selected_file})
        return jsonify({'error': 'AI could not confidently select a file.'}), 404
    except Exception as e:
        return jsonify({'error': f'AI model error: {e}'}), 500

# --- NEW & UPDATED Conversation History Routes ---

@app.route('/conversations', methods=['POST'])
def create_conversation():
    """Creates a new conversation and returns its ID."""
    topic = request.json.get('topic', 'New Chat')
    db = get_db()
    cursor = db.execute("INSERT INTO conversations (topic) VALUES (?)", (topic,))
    db.commit()
    return jsonify({'conversation_id': cursor.lastrowid})

@app.route('/conversations', methods=['GET'])
def get_conversations():
    """Gets the list of all past conversations."""
    db = get_db()
    convos = db.execute("SELECT id, topic, timestamp FROM conversations ORDER BY timestamp DESC").fetchall()
    return jsonify([{'id': row['id'], 'topic': row['topic']} for row in convos])

@app.route('/conversations/<int:conv_id>', methods=['GET'])
def get_conversation_history(conv_id):
    """Gets all messages for a specific conversation."""
    db = get_db()
    messages = db.execute(
        "SELECT sender, message FROM chat_history WHERE conversation_id = ? ORDER BY timestamp ASC",
        (conv_id,)
    ).fetchall()
    return jsonify([{'sender': row['sender'], 'message': row['message']} for row in messages])

@app.route('/save-chat', methods=['POST'])
def save_chat():
    """Saves a message to a specific conversation."""
    data = request.json
    conv_id = data.get('conversation_id')
    sender = data.get('sender')
    message = data.get('message')

    if not all([conv_id, sender, message]):
        return jsonify({'error': 'Missing data'}), 400

    db = get_db()
    db.execute(
        "INSERT INTO chat_history (conversation_id, sender, message) VALUES (?, ?, ?)",
        (conv_id, sender, message)
    )
    db.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)