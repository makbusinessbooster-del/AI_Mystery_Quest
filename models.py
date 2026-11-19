from datetime import datetime
import secrets, string
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    difficulty = db.Column(db.String(20), default="Medium")
    synopsis = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(160), default="Unknown")
    suspects = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text, nullable=False)
    puzzle = db.Column(db.Text, nullable=False)
    hint = db.Column(db.Text, nullable=False)
    solution_keywords = db.Column(db.String(300), nullable=False)
    solution_explanation = db.Column(db.Text, nullable=False)
    is_published = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.String(80), default="system")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    score = db.Column(db.Integer, default=0)
    attempts = db.Column(db.Integer, default=0)
    hints_used = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    last_answer = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    case = db.relationship("Case")

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="waiting")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    case = db.relationship("Case")
    @staticmethod
    def make_code():
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(6))

class RoomPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    score = db.Column(db.Integer, default=0)
    user = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("room_id", "user_id"),)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
