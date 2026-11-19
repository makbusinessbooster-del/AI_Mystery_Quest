import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from extensions import db
from models import User, Case, GameSession, Room, RoomPlayer, ChatMessage
from game_data import STARTER_CASES
from ai_service import generate_case, detective_reply, ai_available
from werkzeug.security import check_password_hash

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-this-secret")
database_url = os.getenv("DATABASE_URL", "sqlite:///mystery_quest.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please sign in to continue."

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def seed_cases():
    if Case.query.count() == 0:
        for item in STARTER_CASES:
            db.session.add(Case(**item, is_published=True, created_by="system"))
        db.session.commit()

with app.app_context():
    db.create_all()
    seed_cases()
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password and not User.query.filter_by(email=admin_email.lower()).first():
        admin = User(username=os.getenv("ADMIN_USERNAME", "admin"),
                     email=admin_email.lower(), is_admin=True)
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()

@app.route("/")
def index():
    cases = Case.query.filter_by(is_published=True).order_by(Case.id).limit(6).all()
    return render_template("index.html", cases=cases, ai_ready=ai_available())

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(username) < 3 or len(password) < 8 or "@" not in email:
            flash("Use a username (3+ chars), valid email and password (8+ chars).", "error")
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash("That username or email is already registered.", "error")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user); db.session.commit()
            login_user(user)
            flash("Account created. Your detective journey begins!", "success")
            return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        user = User.query.filter((User.email == identity.lower()) | (User.username == identity)).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user, remember=True)
            return redirect(url_for("dashboard"))
        flash("Invalid login details.", "error")
    return render_template("auth.html", mode="login")

@app.route("/guest")
def guest():
    # Guest identity is session-scoped; no permanent profile or cloud save.
    from flask import session
    session["guest"] = True
    session["guest_name"] = "Guest Detective"
    return redirect(url_for("dashboard"))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have signed out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if not current_user.is_authenticated:
        from flask import session
        if not session.get("guest"):
            return redirect(url_for("login"))
        name, xp, level = session.get("guest_name", "Guest Detective"), 0, 1
        sessions = []
    else:
        name, xp, level = current_user.username, current_user.xp, current_user.level
        sessions = GameSession.query.filter_by(user_id=current_user.id).order_by(GameSession.updated_at.desc()).limit(5).all()
    cases = Case.query.filter_by(is_published=True).all()
    return render_template("dashboard.html", name=name, xp=xp, level=level, cases=cases, sessions=sessions)

@app.route("/case/<int:case_id>")
def play_case(case_id):
    case = Case.query.filter_by(id=case_id, is_published=True).first_or_404()
    if not current_user.is_authenticated:
        from flask import session
        if not session.get("guest"):
            return redirect(url_for("login"))
        game = None
    else:
        game = GameSession.query.filter_by(user_id=current_user.id, case_id=case.id, completed=False).first()
        if not game:
            game = GameSession(user_id=current_user.id, case_id=case.id)
            db.session.add(game); db.session.commit()
    return render_template("case.html", case=case, game=game)

@app.post("/api/answer")
def submit_answer():
    data = request.get_json(silent=True) or {}
    case = Case.query.filter_by(id=data.get("case_id"), is_published=True).first_or_404()
    answer = str(data.get("answer", "")).strip().lower()
    if not answer:
        return jsonify(error="Enter your theory first."), 400
    correct = any(answer == a.lower() or a.lower() in answer for a in case.solution_keywords.split("|"))
    if current_user.is_authenticated:
        game = GameSession.query.filter_by(user_id=current_user.id, case_id=case.id, completed=False).first()
        if not game:
            game = GameSession(user_id=current_user.id, case_id=case.id)
            db.session.add(game)
        game.attempts += 1
        game.last_answer = answer
        if correct:
            game.completed = True
            game.score += max(50, 150 - game.hints_used * 20 - (game.attempts - 1) * 10)
            current_user.xp += game.score
            current_user.level = 1 + current_user.xp // 500
        db.session.commit()
        score = game.score
    else:
        score = 100 if correct else 0
    return jsonify(correct=correct, message=("Case solved! Excellent detective work." if correct else "Not quite. Review the evidence and try another theory."),
                   score=score, xp=(current_user.xp if current_user.is_authenticated else 0))

@app.post("/api/hint/<int:case_id>")
def hint(case_id):
    case = Case.query.filter_by(id=case_id, is_published=True).first_or_404()
    hint_text = case.hint
    if current_user.is_authenticated:
        game = GameSession.query.filter_by(user_id=current_user.id, case_id=case.id, completed=False).first()
        if not game:
            game = GameSession(user_id=current_user.id, case_id=case.id)
            db.session.add(game)
        if game.hints_used >= 3:
            return jsonify(error="You have used all 3 hints for this case."), 429
        game.hints_used += 1
        db.session.commit()
        remaining = 3 - game.hints_used
    else:
        remaining = "guest"
    return jsonify(hint=hint_text, remaining=remaining)

@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    case = Case.query.filter_by(id=data.get("case_id"), is_published=True).first_or_404()
    question = str(data.get("message", "")).strip()[:500]
    if not question:
        return jsonify(error="Ask a question first."), 400
    if current_user.is_authenticated:
        recent = ChatMessage.query.filter_by(user_id=current_user.id, case_id=case.id).filter(
            ChatMessage.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)).count()
        if recent >= 30:
            return jsonify(error="Daily Detective AI limit reached (30 messages)."), 429
    reply = detective_reply(case, question)
    if current_user.is_authenticated:
        db.session.add(ChatMessage(user_id=current_user.id, case_id=case.id, question=question, answer=reply))
        db.session.commit()
    return jsonify(reply=reply, ai_mode=("Groq" if ai_available() else "Demo"))

@app.route("/leaderboard")
def leaderboard():
    users = User.query.order_by(User.xp.desc()).limit(20).all()
    return render_template("leaderboard.html", users=users)

@app.route("/multiplayer")
@login_required
def multiplayer():
    return render_template("multiplayer.html", cases=Case.query.filter_by(is_published=True).all())

@app.post("/api/rooms")
@login_required
def create_room():
    data = request.get_json(silent=True) or {}
    case_id = data.get("case_id")
    case = Case.query.filter_by(id=case_id, is_published=True).first_or_404()
    room = Room(code=Room.make_code(), case_id=case.id, host_id=current_user.id)
    db.session.add(room); db.session.flush()
    db.session.add(RoomPlayer(room_id=room.id, user_id=current_user.id))
    db.session.commit()
    return jsonify(code=room.code)

@app.post("/api/rooms/join")
@login_required
def join_room():
    data = request.get_json(silent=True) or {}
    room = Room.query.filter_by(code=str(data.get("code", "")).upper(), status="waiting").first()
    if not room:
        return jsonify(error="Room not found or no longer accepting players."), 404
    if RoomPlayer.query.filter_by(room_id=room.id, user_id=current_user.id).first():
        return jsonify(code=room.code)
    if RoomPlayer.query.filter_by(room_id=room.id).count() >= 4:
        return jsonify(error="This room is full (maximum 4 players)."), 400
    db.session.add(RoomPlayer(room_id=room.id, user_id=current_user.id))
    db.session.commit()
    return jsonify(code=room.code)

@app.get("/api/rooms/<code>")
@login_required
def room_state(code):
    room = Room.query.filter_by(code=code.upper()).first_or_404()
    players = RoomPlayer.query.filter_by(room_id=room.id).all()
    return jsonify(code=room.code, status=room.status, case_id=room.case_id,
                   case_title=room.case.title,
                   players=[{"username": p.user.username, "score": p.score} for p in players])

@app.post("/api/rooms/<code>/score")
@login_required
def room_score(code):
    room = Room.query.filter_by(code=code.upper()).first_or_404()
    player = RoomPlayer.query.filter_by(room_id=room.id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    player.score = max(player.score, min(int(data.get("score", 0)), 10000))
    db.session.commit()
    return jsonify(ok=True)

@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        abort(403)
    return render_template("admin.html", users=User.query.order_by(User.id.desc()).all(),
                           cases=Case.query.order_by(Case.id.desc()).all())

@app.post("/admin/case")
@login_required
def admin_case():
    if not current_user.is_admin: abort(403)
    title = request.form.get("title", "").strip()
    if title:
        db.session.add(Case(title=title, category=request.form.get("category","Murder Mystery"),
            difficulty=request.form.get("difficulty","Medium"), synopsis=request.form.get("synopsis",""),
            location=request.form.get("location","Unknown"), suspects=request.form.get("suspects",""),
            evidence=request.form.get("evidence",""), puzzle=request.form.get("puzzle",""),
            hint=request.form.get("hint",""), solution_keywords=request.form.get("solution_keywords",""),
            solution_explanation=request.form.get("solution_explanation",""), is_published=True,
            created_by=current_user.username))
        db.session.commit()
        flash("Case added.", "success")
    return redirect(url_for("admin"))

@app.post("/api/generate-case")
@login_required
def api_generate_case():
    data = request.get_json(silent=True) or {}
    result = generate_case(data.get("category","Murder Mystery"), data.get("difficulty","Medium"))
    if not result:
        return jsonify(error="Groq case generation is unavailable. Add GROQ_API_KEY or use a published case."), 503
    required = ["title","synopsis","location","suspects","evidence","puzzle","hint","solution_keywords","solution_explanation"]
    if any(not result.get(k) for k in required):
        return jsonify(error="AI returned an incomplete case. Please try again."), 502
    case = Case(**{k: result[k] for k in required}, category=data.get("category","Murder Mystery"),
                difficulty=data.get("difficulty","Medium"), is_published=True, created_by="Groq AI")
    db.session.add(case); db.session.commit()
    return jsonify(id=case.id, title=case.title)

@app.errorhandler(403)
def forbidden(_): return render_template("error.html", code=403, message="You do not have permission to access this page."), 403
@app.errorhandler(404)
def missing(_): return render_template("error.html", code=404, message="The requested page was not found."), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG","0") == "1")
