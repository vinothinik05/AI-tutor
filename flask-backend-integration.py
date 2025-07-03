# app.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import sqlite3
import os
import secrets
import qrcode
from io import BytesIO
import base64
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['DATABASE'] = 'users.db'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    with app.app_context():
        conn = get_db_connection()
        with open('schema.sql') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print("Database initialized!")

# Generate a random access code
def generate_access_code():
    # 6 character alphanumeric code
    return ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))

# Generate QR code for group sharing
def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"

# Routes
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        
        # Check if email or username already exists
        existing_user = conn.execute(
            'SELECT * FROM users WHERE email = ? OR username = ?', 
            (email, username)
        ).fetchone()
        
        if existing_user:
            conn.close()
            flash('Email or username already exists', 'error')
            return render_template('register.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        conn.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        conn.commit()
        
        # Get the user_id of the newly created user
        user_id = conn.execute(
            'SELECT user_id FROM users WHERE email = ?', (email,)
        ).fetchone()['user_id']
        
        conn.close()
        
        # Log the user in
        session['user_id'] = user_id
        session['username'] = username
        
        return redirect(url_for('home'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/groups')
def groups():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    # Get groups the user is a member of
    member_groups = conn.execute('''
        SELECT g.*, COUNT(gm.user_id) as member_count
        FROM groups g
        JOIN group_members gm ON g.group_id = gm.group_id
        WHERE g.group_id IN (
            SELECT group_id FROM group_members WHERE user_id = ?
        )
        GROUP BY g.group_id
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return render_template('groups.html', groups=member_groups)

@app.route('/groups/create', methods=['GET', 'POST'])
def create_group():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        is_private = 'privacy' in request.form and request.form['privacy'] == 'private'
        
        # Generate a unique access code
        access_code = generate_access_code()
        
        conn = get_db_connection()
        
        # Check for duplicate access code and regenerate if needed
        while conn.execute('SELECT * FROM groups WHERE access_code = ?', (access_code,)).fetchone():
            access_code = generate_access_code()
        
        # Insert new group
        conn.execute('''
            INSERT INTO groups (name, description, access_code, created_by, is_private)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, access_code, session['user_id'], is_private))
        
        conn.commit()
        
        # Get the group_id of the newly created group
        group_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        # Add the creator as an admin member
        conn.execute('''
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (?, ?, ?)
        ''', (group_id, session['user_id'], 'admin'))
        
        conn.commit()
        conn.close()
        
        # Generate QR code for sharing
        qr_url = request.host_url + f"groups/join?code={access_code}"
        qr_code = generate_qr_code(qr_url)
        
        return jsonify({
            'success': True,
            'group_id': group_id,
            'access_code': access_code,
            'qr_code': qr_code,
            'share_url': qr_url
        })
    
    return render_template('create_group.html')

@app.route('/groups/join', methods=['GET', 'POST'])
def join_group():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    error = None
    
    if request.method == 'POST':
        access_code = request.form['access_code']
        
        conn = get_db_connection()
        group = conn.execute('SELECT * FROM groups WHERE access_code = ?', (access_code,)).fetchone()
        
        if not group:
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid access code'})
        
        # Check if already a member
        existing_member = conn.execute('''
            SELECT * FROM group_members 
            WHERE group_id = ? AND user_id = ?
        ''', (group['group_id'], session['user_id'])).fetchone()
        
        if existing_member:
            conn.close()
            return jsonify({
                'success': True, 
                'already_member': True,
                'group_id': group['group_id']
            })
        
        # Add user as a member
        conn.execute('''
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (?, ?, ?)
        ''', (group['group_id'], session['user_id'], 'member'))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'already_member': False,
            'group_id': group['group_id']
        })
    
    # If GET request with code parameter
    if 'code' in request.args:
        access_code = request.args.get('code')
        conn = get_db_connection()
        group = conn.execute('SELECT * FROM groups WHERE access_code = ?', (access_code,)).fetchone()
        
        if group:
            # Auto-fill the access code on the join form
            return render_template('join_group.html', access_code=access_code)
        else:
            error = 'Invalid access code'
        
        conn.close()
    
    return render_template('join_group.html', error=error)

@app.route('/groups/<int:group_id>')
def view_group(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Check if user is a member
    member = conn.execute('''
        SELECT * FROM group_members 
        WHERE group_id = ? AND user_id = ?
    ''', (group_id, session['user_id'])).fetchone()
    
    if not member:
        conn.close()
        flash('You are not a member of this group', 'error')
        return redirect(url_for('groups'))
    
    # Get group details
    group = conn.execute('SELECT * FROM groups WHERE group_id = ?', (group_id,)).fetchone()
    
    # Get all members
    members = conn.execute('''
        SELECT u.user_id, u.username, u.profile_image, gm.role, gm.joined_at
        FROM users u
        JOIN group_members gm ON u.user_id = gm.user_id
        WHERE gm.group_id = ?
        ORDER BY gm.role = 'admin' DESC, u.username
    ''', (group_id,)).fetchall()
    
    # Get recent messages
    messages = conn.execute('''
        SELECT m.*, u.username, u.profile_image
        FROM messages m
        JOIN users u ON m.user_id = u.user_id
        WHERE m.group_id = ?
        ORDER BY m.created_at DESC
        LIMIT 50
    ''', (group_id,)).fetchall()
    
    # Reverse messages to show oldest first
    messages = list(reversed(messages))
    
    # Get message reactions
    reactions = conn.execute('''
        SELECT mr.*, u.username
        FROM message_reactions mr
        JOIN users u ON mr.user_id = u.user_id
        WHERE mr.message_id IN (SELECT message_id FROM messages WHERE group_id = ?)
    ''', (group_id,)).fetchall()
    
    # Organize reactions by message
    reaction_map = {}
    for reaction in reactions:
        message_id = reaction['message_id']
        if message_id not in reaction_map:
            reaction_map[message_id] = []
        reaction_map[message_id].append({
            'emoji': reaction['emoji'],
            'username': reaction['username'],
            'user_id': reaction['user_id']
        })
    
    conn.close()
    
    return render_template(
        'chat.html', 
        group=group, 
        members=members, 
        messages=messages,
        reactions=reaction_map,
        user_id=session['user_id'],
        username=session['username'],
        user_role=member['role']
    )

@app.route('/api/groups/<int:group_id>/messages', methods=['POST'])
def post_message(group_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    content = request.form.get('content')
    message_type = request.form.get('type', 'text')
    mentioned_user_id = request.form.get('mentioned_user_id')
    file_path = None
    
    # Handle file uploads
    if 'file' in request.files and request.files['file'].filename:
        file = request.files['file']
        filename = secure_filename(file.filename)
        
        # Create unique filename
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        
        file_path = os.path.join('uploads', unique_filename)
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(full_path)
    
    conn = get_db_connection()
    
    # Check if user is a member
    member = conn.execute('''
        SELECT * FROM group_members 
        WHERE group_id = ? AND user_id = ?
    ''', (group_id, session['user_id'])).fetchone()
    
    if not member:
        conn.close()
        return jsonify({'success': False, 'message': 'Not a member of this group'}), 403
    
    # Insert message
    cursor = conn.execute('''
        INSERT INTO messages 
        (group_id, user_id, content, message_type, file_path, mentioned_user_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (group_id, session['user_id'], content, message_type, file_path, mentioned_user_id))
    
    message_id = cursor.lastrowid
    conn.commit()
    
    # Get user info
    user = conn.execute('SELECT username, profile_image FROM users WHERE user_id = ?', 
                       (session['user_id'],)).fetchone()
    
    conn.close()
    
    # Format the response
    message = {
        'message_id': message_id,
        'user_id': session['user_id'],
        'username': user['username'],
        'profile_image': user['profile_image'],
        'content': content,
        'message_type': message_type,
        'file_path': file_path,
        'mentioned_user_id': mentioned_user_id,
        'created_at': datetime.now().isoformat(),
        'is_read': 0,
        'reactions': []
    }
    
    return jsonify({'success': True, 'message': message})

@app.route('/api/messages/<int:message_id>/react', methods=['POST'])
def react_to_message(message_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    emoji = request.json.get('emoji')
    
    conn = get_db_connection()
    
    # Check if message exists and get its group_id
    message = conn.execute('SELECT group_id FROM messages WHERE message_id = ?', (message_id,)).fetchone()
    
    if not message:
        conn.close()
        return jsonify({'success': False, 'message': 'Message not found'}), 404
    
    # Check if user is a member of the group
    member = conn.execute('''
        SELECT * FROM group_members 
        WHERE group_id = ? AND user_id = ?
    ''', (message['group_id'], session['user_id'])).fetchone()
    
    if not member:
        conn.close()
        return jsonify({'success': False, 'message': 'Not a member of this group'}), 403
    
    # Check if reaction already exists
    existing = conn.execute('''
        SELECT * FROM message_reactions 
        WHERE message_id = ? AND user_id = ? AND emoji = ?
    ''', (message_id, session['user_id'], emoji)).fetchone()
    
    if existing:
        # Remove existing reaction (toggle behavior)
        conn.execute('''
            DELETE FROM message_reactions 
            WHERE message_id = ? AND user_id = ? AND emoji = ?
        ''', (message_id, session['user_id'], emoji))
        action = 'removed'
    else:
        # Add new reaction
        conn.execute('''
            INSERT INTO message_reactions (message_id, user_id, emoji)
            VALUES (?, ?, ?)
        ''', (message_id, session['user_id'], emoji))
        action = 'added'
    
    conn.commit()
    
    # Get current reactions for this message
    reactions = conn.execute('''
        SELECT mr.*, u.username
        FROM message_reactions mr
        JOIN users u ON mr.user_id = u.user_id
        WHERE mr.message_id = ?
    ''', (message_id,)).fetchall()
    
    formatted_reactions = []
    for reaction in reactions:
        formatted_reactions.append({
            'emoji': reaction['emoji'],
            'username': reaction['username'],
            'user_id': reaction['user_id']
        })
    
    conn.close()
    
    return jsonify({
        'success': True, 
        'action': action,
        'reactions': formatted_reactions
    })

@app.route('/api/groups/<int:group_id>/typing', methods=['POST'])
def update_typing_status(group_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    is_typing = request.json.get('typing', False)
    
    conn = get_db_connection()
    
    # Check if user is a member
    member = conn.execute('''
        SELECT * FROM group_members 
        WHERE group_id = ? AND user_id = ?
    ''', (group_id, session['user_id'])).fetchone()
    
    if not member:
        conn.close()
        return jsonify({'success': False, 'message': 'Not a member of this group'}), 403
    
    # Update typing status
    existing = conn.execute('''
        SELECT * FROM typing_status 
        WHERE group_id = ? AND user_id = ?
    ''', (group_id, session['user_id'])).fetchone()
    
    if existing:
        conn.execute('''
            UPDATE typing_status
            SET is_typing = ?, last_updated = CURRENT_TIMESTAMP
            WHERE group_id = ? AND user_id = ?
        ''', (1 if is_typing else 0, group_id, session['user_id']))
    else:
        conn.execute('''
            INSERT INTO typing_status (group_id, user_id, is_typing)
            VALUES (?, ?, ?)
        ''', (group_id, session['user_id'], 1 if is_typing else 0))
    
    conn.commit()
    
    # Get list of users currently typing
    typing_users = conn.execute('''
        SELECT u.username 
        FROM typing_status ts
        JOIN users u ON ts.user_id = u.user_id
        WHERE ts.group_id = ? AND ts.user_id != ? AND ts.is_typing = 1
        AND ts.last_updated > datetime('now', '-10 seconds')
    ''', (group_id, session['user_id'])).fetchall()
    
    typing_usernames = [user['username'] for user in typing_users]
    
    conn.close()
    
    return jsonify({
        'success': True,
        'typing_users': typing_usernames
    })

@app.route('/api/groups/<int:group_id>/posts', methods=['GET', 'POST'])
def group_posts(group_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    
    # Check if user is a member
    member = conn.execute('''
        SELECT * FROM group_members 
        WHERE group_id = ? AND user_id = ?
    ''', (group_id, session['user_id'])).fetchone()
    
    if not member:
        conn.close()
        return jsonify({'success': False, 'message': 'Not a member of this group'}), 403
    
    if request.method == 'POST':
        content = request.form.get('content')
        
        # Handle file uploads
        attachments = []
        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            for file in files:
                if file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    unique_filename = f"{timestamp}_{filename}"
                    
                    file_path = os.path.join('uploads', unique_filename)
                    full_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(full_path)
                    
                    file_type = file.content_type if hasattr(file, 'content_type') else 'application/octet-stream'
                    attachments.append({
                        'file_name': filename,
                        'file_type': file_type,
                        'file_path': file_path
                    })
        
        # Insert post
        cursor = conn.execute('''
            INSERT INTO posts (group_id, user_id, content)
            VALUES (?, ?, ?)
        ''', (group_id, session['user_id'], content))
        
        post_id = cursor.lastrowid
        
        # Add attachments
        for attachment in attachments:
            conn.execute('''
                INSERT INTO post_attachments (post_id, file_name, file_type, file_path)
                VALUES (?, ?, ?, ?)
            ''', (post_id, attachment['file_name'], attachment['file_type'], attachment['file_path']))
        
        conn.commit()
        
        # Get the newly created post with user details
        post = conn.execute('''
            SELECT p.*, u.username, u.profile_image
            FROM posts p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.post_id = ?
        ''', (post_id,)).fetchone()
        
        # Get post attachments
        post_attachments = conn.execute('''
            SELECT * FROM post_attachments
            WHERE post_id = ?
        ''', (post_id,)).fetchall()
        
        formatted_post = dict(post)
        formatted_post['attachments'] = [dict(attachment) for attachment in post_attachments]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'post': formatted_post
        })
    else:
        # Get posts for this group
        posts = conn.execute('''
            SELECT p.*, u.username, u.profile_image
            FROM posts p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.group_id = ?
            ORDER BY p.created_at DESC
        ''', (group_id,)).fetchall()
        
        # Get all post IDs
        post_ids = [post['post_id'] for post in posts]
        
        # Get attachments for these posts
        attachments = {}
        if post_ids:
            # Create placeholders for SQL query
            placeholders = ','.join(['?'] * len(post_ids))
            all_attachments = conn.execute(f'''
                SELECT * FROM post_attachments
                WHERE post_id IN ({placeholders})
            ''', post_ids).fetchall()
            
            # Group attachments by post_id
            for attachment in all_attachments:
                post_id = attachment['post_id']
                if post_id not in attachments:
                    attachments[post_id] = []
                attachments[post_id].append(dict(attachment))
        
        # Get comments for these posts
        comments = {}
        if post_ids:
            all_comments = conn.execute(f'''
                SELECT c.*, u.username, u.profile_image
                FROM comments c
                JOIN users u ON c.user_id = u.user_id
                WHERE c.post_id IN ({placeholders})
                ORDER BY c.created_at
            ''', post_ids).fetchall()
            
            # Group comments by post_id
            for comment in all_comments:
                post_id = comment['post_id']
                if post_id not in comments:
                    comments[post_id] = []
                comments[post_id].append(dict(comment))
        
        # Format posts with attachments and comments
        formatted_posts = []
        for post in posts:
            post_dict = dict(post)
            post_dict['attachments'] = attachments.get(post['post_id'], [])
            post_dict['comments'] = comments.get(post['post_id'], [])
            formatted_posts.append(post_dict)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'posts': formatted_posts
        })

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    content = request.json.get('content')
    
    conn = get_db_connection()
    
    # Get post details to check group membership
    post = conn.execute('SELECT group_id FROM posts WHERE post_id = ?', (post_id,)).fetchone()
    
    if not post:
        conn.close()
        return jsonify({'success': False, 'message': 'Post not found'}), 404
    
    # Check if user is a member of the group
    member = conn.execute('''
        SELECT * FROM group_members 
        WHERE group_id = ? AND user_id = ?
    ''', (post['group_id'], session['user_id'])).fetchone()
    
    if not member:
        conn.close()
        return jsonify({'success': False, 'message': 'Not a member of this group'}), 403
    
    # Add comment
    cursor = conn.execute('''
        INSERT INTO comments (post_id, user_id, content)
        VALUES (?, ?, ?)
    ''', (post_id, session['user_id'], content))
    
    comment_id = cursor.lastrowid
    conn.commit()
    
    # Get the newly added comment with user details
    comment = conn.execute('''
        SELECT c.*, u.username, u.profile_image
        FROM comments c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.comment_id = ?
    ''', (comment_id,)).fetchone()
    
    conn.close()
    
    return jsonify({
        'success': True,
        'comment': dict(comment)
    })

@app.route('/api/groups/<int:group_id>/regenerate-code', methods=['POST'])
def regenerate_access_code(group_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    
    # Check if user is an admin
    member = conn.execute('''
        SELECT role FROM group_members 
        WHERE group_id = ? AND user_id = ?
    ''', (group_id, session['user_id'])).fetchone()
    
    if not member or member['role'] != 'admin':
        conn.close()
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    # Generate new access code
    new_code = generate_access_code()
    
    # Check for duplicates
    while conn.execute('SELECT * FROM groups WHERE access_code = ?', (new_code,)).fetchone():
        new_code = generate_access_code()
    
    # Update group with new code
    conn.execute('''
        UPDATE groups
        SET access_code = ?
        WHERE group_id = ?
    ''', (new_code, group_id))
    
    conn.commit()
    
    # Generate QR code for sharing
    qr_url = request.host_url + f"groups/join?code={new_code}"
    qr_code = generate_qr_code(qr_url)
    
    conn.close()
    
    return jsonify({
        'success': True,
        'new_code': new_code,
        'qr_code': qr_code,
        'share_url': qr_url
    })

# Run the application
if __name__ == '__main__':
    # Uncomment to initialize database (first run only)
    # init_db()
    #app.run(debug=True)
    app.run(port=5001)
