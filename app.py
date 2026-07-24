import os
import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

import db
import ai
import email_alert

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret')

@app.teardown_appcontext
def close_connection(exception):
    db.close_db(exception)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user(session['user_id'])
    if user['role'] == 'guardian':
        return redirect(url_for('guardian_dashboard'))
    return redirect(url_for('chat'))

def get_user(user_id):
    conn = db.get_db()
    return conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = db.get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        return "Invalid credentials", 400
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        guardian_email = request.form.get('guardian_email', '')
        
        conn = db.get_db()
        try:
            conn.execute(
                'INSERT INTO users (username, password_hash, role, guardian_email) VALUES (?, ?, ?, ?)',
                (username, generate_password_hash(password), role, guardian_email)
            )
            conn.commit()
            return redirect(url_for('login'))
        except db.sqlite3.IntegrityError:
            return "Username already exists", 400
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = db.get_db()
    users = conn.execute('SELECT id, username, role FROM users WHERE id != ?', (session['user_id'],)).fetchall()
    
    chat_with = request.args.get('user_id', type=int)
    return render_template('chat.html', users=users, chat_with=chat_with, current_user=get_user(session['user_id']))

@app.route('/api/messages/<int:chat_id>', methods=['GET'])
def get_messages(chat_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    my_id = session['user_id']
    conn = db.get_db()
    messages = conn.execute('''
        SELECT m.*, u.username as sender_name 
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
        ORDER BY timestamp ASC
    ''', (my_id, chat_id, chat_id, my_id)).fetchall()
    
    return jsonify([dict(m) for m in messages])

@app.route('/api/messages/<int:chat_id>', methods=['POST'])
def send_message(chat_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    text = request.json.get('text', '')
    if not text:
        return jsonify({'error': 'Empty message'}), 400
        
    my_id = session['user_id']
    timestamp = datetime.datetime.utcnow().isoformat()
    
    analysis = ai.classify_message(text)
    
    conn = db.get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (sender_id, receiver_id, text, severity, is_bullying, reason, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (my_id, chat_id, text, analysis['severity'], analysis['is_bullying'], analysis['reason'], timestamp))
    message_id = cursor.lastrowid
    
    if analysis['severity'] in ['flagged', 'high']:
        cursor.execute('''
            INSERT INTO alerts (message_id, confidence, timestamp)
            VALUES (?, ?, ?)
        ''', (message_id, analysis['confidence'], timestamp))
        
        if analysis['severity'] == 'high' and os.getenv('EMAIL_ENABLED', 'false').lower() == 'true':
            my_user = get_user(my_id)
            if my_user['guardian_email']:
                email_alert.send_alert(my_user['guardian_email'], text, analysis['reason'])
            
            suggested_reply = analysis.get('suggested_reply') or 'This message was flagged for severe bullying.'
            auto_timestamp = datetime.datetime.utcnow().isoformat()
            cursor.execute('''
                INSERT INTO messages (sender_id, receiver_id, text, severity, is_bullying, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (chat_id, my_id, suggested_reply, 'safe', False, 'Auto-reply from system', auto_timestamp))
            
    conn.commit()
    return jsonify({'status': 'ok'})

@app.route('/guardian')
def guardian_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user(session['user_id'])
    if user['role'] != 'guardian':
        return redirect(url_for('chat'))
        
    conn = db.get_db()
    alerts = conn.execute('''
        SELECT a.id as alert_id, a.confidence, a.status, a.timestamp as alert_time,
               m.text, m.severity, m.reason, m.sender_id, u.username as sender_name
        FROM alerts a
        JOIN messages m ON a.message_id = m.id
        JOIN users u ON m.sender_id = u.id
        ORDER BY a.timestamp DESC
    ''').fetchall()
    
    return render_template('guardian.html', alerts=alerts)

@app.route('/api/alerts/<int:alert_id>/status', methods=['POST'])
def update_alert(alert_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    status = request.json.get('status')
    if status not in ['resolved', 'ignored']:
        return jsonify({'error': 'Invalid status'}), 400
        
    conn = db.get_db()
    conn.execute('UPDATE alerts SET status = ? WHERE id = ?', (status, alert_id))
    conn.commit()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    db.init_db()
    app.run(debug=True)
