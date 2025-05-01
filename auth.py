# auth.py — handles user registration and login
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

bp = Blueprint('auth', __name__)

DB_PATH = 'users.db'

# Initialize DB
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL
                    )''')
        conn.commit()

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hash_pw = generate_password_hash(password)

        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_pw))
                conn.commit()
                flash('Account created. Please log in.', 'success')
                return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'error')

    return render_template('signup.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
            result = c.fetchone()

            if result and check_password_hash(result[1], password):
                session['user_id'] = result[0]
                session['username'] = username
                flash('Logged in successfully.', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid credentials.', 'error')

    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))
