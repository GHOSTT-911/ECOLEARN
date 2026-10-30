from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "ecolearn.db")
SITE_DIR = BASE_DIR  # index.html sits next to app.py (same file Netlify serves)

app = Flask(__name__, static_folder=SITE_DIR, static_url_path="/static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

CORS(app, supports_credentials=True)  # allow frontend to call APIs

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# ----------------------
# Models
# ----------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    badges = db.relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    quiz_results = db.relationship("QuizResult", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

class Badge(db.Model):
    __tablename__ = "badges"
    id = db.Column(db.Integer, primary_key=True)
    badge_id = db.Column(db.String(100), unique=True, nullable=False)  # like 'sustainability-master'
    title = db.Column(db.String(200), nullable=False)
    icon = db.Column(db.String(500), nullable=True)

    users = db.relationship("UserBadge", back_populates="badge", cascade="all, delete-orphan")

class UserBadge(db.Model):
    __tablename__ = "user_badges"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"))
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="badges")
    badge = db.relationship("Badge", back_populates="users")

class QuizResult(db.Model):
    __tablename__ = "quiz_results"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    lesson = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)  # percentage 0-100
    raw_score = db.Column(db.Integer, nullable=False) # number correct
    total_questions = db.Column(db.Integer, nullable=False)
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="quiz_results")

# ----------------------
# Load / create DB
# ----------------------
def init_db():
    if not os.path.exists(DB_PATH):
        with app.app_context(): 
            db.create_all()
            seed_badges()
            seed_leaderboard()
            print("Database created and seeded.")

def seed_badges():
    # badges from your frontend
    badges = [
        ("sustainability-master", "Sustainability Scholar", "https://imgcdn.stablediffusionweb.com/2024/12/12/17028fba-13a3-46fc-ad2b-516ad5dd9496.jpg"),
        ("renewable-master", "Renewable Energy Guru", "https://thumbs.dreamstime.com/b/energy-saver-item-seal-22992650.jpg"),
        ("waste-management-master", "Waste Warrior", "https://devp.org/wp-content/uploads/2023/11/02.-Tree-Planter.png"),
        ("eco-champion", "Eco Champion", "https://file.aiquickdraw.com/imgcompressed/img/compressed_f31a088e7442a3f80431c151bb9783ec.webp"),
        ("green-pioneer", "Green Pioneer", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQFaOnJmjr1qJbtA-hJp1oFjdmAQK0VvWUfrOk2cCL3z0EWA5oDMBsEeHTlByn5KwMuBC0&usqp=CAU"),
    ]
    for bid, title, icon in badges:
        b = Badge(badge_id=bid, title=title, icon=icon)
        db.session.add(b)
    db.session.commit()

def seed_leaderboard():
    # example leaderboard users (create local-only users)
    sample = [
        ("EcoHero1", "eco1@example.com", "password", 95),
        ("GreenGenius", "gg@example.com", "password", 91),
        ("PlanetSaver", "ps@example.com", "password", 89),
    ]
    for username, email, pwd, score in sample:
        if not User.query.filter_by(username=username).first():
            u = User(username=username, email=email)
            u.set_password(pwd)
            db.session.add(u)
            db.session.flush()
            qr = QuizResult(user_id=u.id, lesson="seeded", score=score, raw_score=score, total_questions=100)
            db.session.add(qr)
    db.session.commit()

# ----------------------
# Login manager
# ----------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------------
# Simple lesson answer store (server-side canonical answers)
# ----------------------
# These must correspond to your frontend correctAnswers mapping
CANONICAL_ANSWERS = {
    'sustainability': {
        's1': 'i', 's2': 'iii', 's3': 'iii', 's4': 'ii', 's5': 'ii',
        's6': 'ii', 's7': 'iii', 's8': 'i', 's9': 'ii', 's10': 'ii'
    },
    'renewable': {
        'r1': 'ii', 'r2': 'ii', 'r3': 'ii', 'r4': 'iv', 'r5': 'ii',
        'r6': 'ii', 'r7': 'iii', 'r8': 'iii', 'r9': 'ii', 'r10': 'ii'
    },
    'waste-management': {
        'w1': 'i', 'w2': 'iii', 'w3': 'ii', 'w4': 'iii', 'w5': 'ii',
        'w6': 'i', 'w7': 'ii', 'w8': 'ii', 'w9': 'iii', 'w10': 'ii'
    }
}

BADGE_MAPPING = {
    'sustainability': 'sustainability-master',
    'renewable': 'renewable-master',
    'waste-management': 'waste-management-master'
}

# ----------------------
# Routes: static + index
# ----------------------
@app.route("/")
def index():
    # serve index.html from the project root (same file Netlify serves)
    return send_from_directory(SITE_DIR, "index.html")

# serve all other static if needed
@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(SITE_DIR, filename)

# ----------------------
# API endpoints
# ----------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"ok": False, "error": "username, email and password required"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"ok": False, "error": "username or email already exists"}), 400

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"ok": True, "message": "registered"})

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"ok": False, "error": "invalid username or password"}), 401

    login_user(user)
    # minimal JSON user info
    return jsonify({"ok": True, "user": {"id": user.id, "username": user.username, "email": user.email}})

@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"ok": True, "message": "logged out"})

@app.route("/api/current_user", methods=["GET"])
def api_current_user():
    if current_user.is_authenticated:
        u = current_user
        # collect user's badges
        user_badges = [
            {"badge_id": ub.badge.badge_id, "title": ub.badge.title, "icon": ub.badge.icon, "awarded_at": ub.awarded_at.isoformat()}
            for ub in u.badges
        ]
        return jsonify({"ok": True, "user": {"id": u.id, "username": u.username, "email": u.email, "badges": user_badges}})
    else:
        return jsonify({"ok": True, "user": None})

@app.route("/api/badges", methods=["GET"])
def api_badges():
    # return list of all badges
    badges = Badge.query.all()
    out = [{"badge_id": b.badge_id, "title": b.title, "icon": b.icon} for b in badges]
    return jsonify({"ok": True, "badges": out})

@app.route("/api/user_badges", methods=["GET"])
@login_required
def api_user_badges():
    u = current_user
    user_badges = [
        {"badge_id": ub.badge.badge_id, "title": ub.badge.title, "icon": ub.badge.icon, "awarded_at": ub.awarded_at.isoformat()}
        for ub in u.badges
    ]
    return jsonify({"ok": True, "badges": user_badges})

@app.route("/api/submit_quiz", methods=["POST"])
def api_submit_quiz():
    """
    Expected JSON:
    {
      "lesson": "sustainability",
      "answers": { "s1": "i", "s2": "iii", ... }
    }
    If user is logged in, award badges and save QuizResult to that user.
    """
    data = request.get_json() or {}
    lesson = data.get("lesson")
    answers = data.get("answers", {})

    if lesson not in CANONICAL_ANSWERS:
        return jsonify({"ok": False, "error": "unknown lesson"}), 400

    canonical = CANONICAL_ANSWERS[lesson]
    total = len(canonical)
    correct = 0
    unanswered = 0
    for qname, correct_ans in canonical.items():
        if qname not in answers or answers[qname] is None or answers[qname] == "":
            unanswered += 1
        else:
            if answers[qname] == correct_ans:
                correct += 1

    percentage = round((correct / total) * 100) if total > 0 else 0

    # persist quiz result (if logged in)
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
        qr = QuizResult(user_id=user_id, lesson=lesson, score=percentage, raw_score=correct, total_questions=total)
        db.session.add(qr)

        # award badge if >= 80
        awarded_badge = None
        if percentage >= 80:
            badge_key = BADGE_MAPPING.get(lesson)
            if badge_key:
                badge = Badge.query.filter_by(badge_id=badge_key).first()
                if badge:
                    # check if user already has it
                    if not any(ub.badge_id == badge.id for ub in current_user.badges):
                        ub = UserBadge(user_id=current_user.id, badge_id=badge.id)
                        db.session.add(ub)
                        awarded_badge = {"badge_id": badge.badge_id, "title": badge.title, "icon": badge.icon}
        db.session.commit()
    else:
        # anonymous submission: still create standalone result (user_id=None)
        qr = QuizResult(user_id=None, lesson=lesson, score=percentage, raw_score=correct, total_questions=total)
        db.session.add(qr)
        db.session.commit()

    # update leaderboard: we'll compute leaderboard from best user QuizResult score per user
    # returning result
    resp = {
        "ok": True,
        "score": percentage,
        "correct": correct,
        "total": total,
        "unanswered": unanswered,
        "awarded_badge": awarded_badge if 'awarded_badge' in locals() else None
    }
    return jsonify(resp)

@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    # For each user, take their best score (max QuizResult.score)
    rows = db.session.query(User.username, db.func.max(QuizResult.score).label("best_score"))             .join(QuizResult, QuizResult.user_id == User.id)             .group_by(User.id).order_by(db.desc("best_score")).limit(50).all()
    out = []
    for idx, row in enumerate(rows):
        out.append({"rank": idx + 1, "name": row[0], "score": int(row[1])})
    # add seeded anonymous or others if you want; also include top global seeded ones maybe
    return jsonify({"ok": True, "leaderboard": out})

# ----------------------
# Start up
# ----------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
