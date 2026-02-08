from flask import Flask, request, jsonify, render_template, redirect, url_for, session, abort
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os, requests
import mysql.connector
from mysql.connector import Error

# --- CONFIG ---
load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY") or ""
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or ""
SEARCHAPI_KEY = os.getenv("SEARCHAPI_KEY") or ""

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_DATABASE = os.getenv("DB_DATABASE", "newsapp_db")

FREE_USER_LIMIT = 3
PAID_USER_LIMIT = 10
FREE_VIDEO_LIMIT = 3
PAID_VIDEO_LIMIT = 6

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.urandom(24)

# === DB SYSTEM ===

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE
    )

def execute_query(query, params=None, fetch=False, commit=False):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())

        if commit:
            conn.commit()
            return cursor.lastrowid

        if fetch:
            return cursor.fetchall()

        return True

    except Error as e:
        print("[DB ERROR]", e)
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# === DECORATORS ===

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# === AUTH ===

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')

        if not (name and email and password):
            return render_template('signup.html', error="All fields are required.")

        hashed = generate_password_hash(password)
        res = execute_query(
            "INSERT INTO users (name, email, password, role, plan) VALUES (%s,%s,%s,'user','free')",
            (name, email, hashed),
            commit=True
        )

        if res:
            u = execute_query("SELECT id FROM users WHERE email=%s", (email,), fetch=True)
            session['user_id'] = u[0]['id']
            session['name'] = name
            session['role'] = 'user'
            session['plan'] = 'free'
            return redirect(url_for('dashboard'))

        return render_template('signup.html', error="Email already exists.")

    return render_template('signup.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password')

        rows = execute_query("SELECT * FROM users WHERE email=%s", (email,), fetch=True)
        if rows:
            u = rows[0]
            if check_password_hash(u['password'], password):
                session['user_id'] = u['id']
                session['name'] = u['name']
                session['role'] = u['role']
                session['plan'] = u['plan']

                if u['role'] == 'admin':
                    return redirect(url_for('admin_panel'))
                return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid email or password.")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# === PAGES ===

@app.route('/')
def index():
    return render_template('index.html', session=session)

@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    saved = execute_query(
        "SELECT title, source, url FROM saved_articles WHERE user_id=%s ORDER BY published_at DESC LIMIT 5",
        (uid,),
        fetch=True
    ) or []
    return render_template('dashboard.html', saved_articles=saved, session=session)

@app.route('/upgrade')
@login_required
def upgrade():
    return render_template('upgrade.html', session=session)

@app.route('/saved_articles')
@login_required
def saved_articles():
    uid = session['user_id']
    rows = execute_query(
        "SELECT title, url, source, DATE_FORMAT(published_at,'%%Y-%%m-%%d') AS published_date "
        "FROM saved_articles WHERE user_id=%s ORDER BY published_at DESC",
        (uid,),
        fetch=True
    ) or []
    return render_template('saved_articles.html', articles=rows, session=session)

# === NEWS API ===

@app.route('/api/news')
@login_required
def api_news():
    topic = request.args.get('topic','').strip()
    sort = request.args.get('sort','publishedAt')
    plan = session.get('plan','free')
    uid = session['user_id']

    if not topic:
        return jsonify({"error":"Topic missing"}), 400

    limit = PAID_USER_LIMIT if plan == "paid" else FREE_USER_LIMIT

    url = (
        "https://newsapi.org/v2/everything"
        f"?q={requests.utils.quote(topic)}"
        f"&sortBy={sort}"
        f"&apiKey={NEWSAPI_KEY}"
        f"&pageSize=20"
    )

    try:
        r = requests.get(url, timeout=10).json()

        if r.get("status") != "ok":
            msg = r.get("message","API error")
            execute_query("INSERT INTO api_warnings (warning_message) VALUES (%s)", (msg,), commit=True)
            return jsonify({"error": msg}), 500

        articles = r.get("articles", [])[:limit]

        execute_query(
            "INSERT INTO search_tracking (user_id, topic, articles_shown) VALUES (%s,%s,%s)",
            (uid, topic, len(articles)),
            commit=True
        )

        return jsonify([
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "source": a.get("source",{}).get("name"),
                "published_at": a.get("publishedAt")
            } for a in articles
        ])

    except Exception as e:
        execute_query("INSERT INTO api_warnings (warning_message) VALUES (%s)", (str(e),), commit=True)
        return jsonify({"error": str(e)}), 500

# === SAVE ARTICLE ===

@app.route('/api/save_article', methods=['POST'])
@login_required
def api_save_article():
    data = request.get_json() or {}
    user_id = session['user_id']

    if not all([data.get("title"), data.get("url"), data.get("source")]):
        return jsonify({"status":"error", "message":"missing"}), 400

    try:
        execute_query(
            "INSERT INTO saved_articles (user_id,title,url,source,published_at) VALUES (%s,%s,%s,%s,%s)",
            (user_id, data['title'], data['url'], data['source'], data.get('published_at')),
            commit=True
        )
        return jsonify({"status":"success"})
    except:
        return jsonify({"status":"warning","message":"Already saved"}), 200

# === ADMIN ===

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password')

        rows = execute_query(
            "SELECT * FROM users WHERE email=%s AND role='admin'",
            (email,),
            fetch=True
        )

        if rows and check_password_hash(rows[0]['password'], password):
            a = rows[0]
            session['user_id'] = a['id']
            session['name'] = a['name']
            session['role'] = a['role']
            session['plan'] = a['plan']
            return redirect(url_for('admin_panel'))

        return render_template('admin_login.html', error="Invalid admin credentials.")

    return render_template('admin_login.html')

@app.route('/admin/panel')
@admin_required
def admin_panel():
    stats = execute_query("""
        SELECT 
           (SELECT COUNT(*) FROM users) AS total_users,
           (SELECT COUNT(*) FROM users WHERE plan='free') AS free_users,
           (SELECT COUNT(*) FROM users WHERE plan='paid') AS paid_users,
           (SELECT COUNT(*) FROM search_tracking WHERE DATE(timestamp)=CURDATE()) AS total_searches_today,
           (SELECT IFNULL(SUM(articles_shown),0) FROM search_tracking WHERE DATE(timestamp)=CURDATE()) AS total_articles_shown_today
    """, fetch=True)[0]

    warnings = execute_query("SELECT * FROM api_warnings ORDER BY timestamp DESC LIMIT 10", fetch=True) or []

    return render_template('admin_panel.html', stats=stats, warnings=warnings, session=session)

@app.route('/admin/analytics')
@admin_required
def analytics():
    daily_searches = execute_query("""
        SELECT DATE(timestamp) AS search_date, COUNT(*) AS total_searches
        FROM search_tracking
        WHERE DATE(timestamp) >= CURDATE() - INTERVAL 7 DAY
        GROUP BY DATE(timestamp)
        ORDER BY DATE(timestamp) ASC
    """, fetch=True) or []

    most_searched = execute_query("""
        SELECT topic, COUNT(*) AS topic_count
        FROM search_tracking
        GROUP BY topic
        ORDER BY topic_count DESC
        LIMIT 10
    """, fetch=True) or []

    top_users = execute_query("""
        SELECT u.name, COUNT(s.id) AS search_count
        FROM users u
        JOIN search_tracking s ON u.id = s.user_id
        GROUP BY u.id
        ORDER BY search_count DESC
        LIMIT 10
    """, fetch=True) or []

    recent_searches = execute_query("""
        SELECT u.name, s.topic, s.articles_shown, s.timestamp
        FROM search_tracking s
        JOIN users u ON u.id = s.user_id
        ORDER BY s.timestamp DESC
        LIMIT 20
    """, fetch=True) or []

    return render_template(
        'analytics.html',
        daily_searches=daily_searches,
        most_searched=most_searched,
        top_users=top_users,
        recent_searches=recent_searches,
        session=session
    )

@app.route('/admin/manage_users')
@admin_required
def manage_users():
    users = execute_query("SELECT id,name,email,role,plan FROM users ORDER BY id DESC", fetch=True)
    return render_template('view_users.html', users=users, session=session)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    execute_query("DELETE FROM users WHERE id=%s", (user_id,), commit=True)
    return redirect(url_for('manage_users'))

@app.route('/admin/change_plan/<int:user_id>', methods=['POST'])
@admin_required
def change_plan(user_id):
    new_plan = request.form.get("new_plan")
    if new_plan in ("free","paid"):
        execute_query("UPDATE users SET plan=%s WHERE id=%s", (new_plan, user_id), commit=True)
        if session['user_id'] == user_id:
            session['plan'] = new_plan
    return redirect(url_for('manage_users'))

# === CREATE DEFAULT ADMIN ===

def setup_admin():
    rows = execute_query("SELECT * FROM users WHERE role='admin' LIMIT 1", fetch=True)
    if not rows:
        print("Creating default admin (admin@news.com / adminpass)")
        hashed = generate_password_hash("adminpass")
        execute_query(
            "INSERT INTO users (name,email,password,role,plan) VALUES (%s,%s,%s,'admin','paid')",
            ("Admin User", "admin@news.com", hashed),
            commit=True
        )

# === FIXED VIDEO API ===

@app.route("/api/videos")
@login_required
def api_videos():
    topic = request.args.get("topic", "").strip()

    if not topic:
        return jsonify({"error": "topic missing"}), 400

    if not SEARCHAPI_KEY:
        return jsonify({"error": "SearchAPI key missing"}), 500

    url = f"https://www.searchapi.io/api/v1/search?engine=youtube&q={topic}&api_key={SEARCHAPI_KEY}"

    try:
        response = requests.get(url)
        data = response.json()

        videos = []
        if "videos" in data:
            for v in data["videos"]:
                videos.append({
                    "title": v.get("title"),
                    "thumbnail": v.get("thumbnail"),
                    "channel": v.get("channel", {}).get("name", "Unknown"),
                    "url": v.get("link")
                })

        plan = session.get("plan", "free")
        limit = PAID_VIDEO_LIMIT if plan == "paid" else FREE_VIDEO_LIMIT

        return jsonify(videos[:limit])

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === RUN ===

if __name__ == '__main__':
    setup_admin()
    app.run(debug=True, host="127.0.0.1", port=5000)
