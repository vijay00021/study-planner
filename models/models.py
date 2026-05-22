from extensions import db
from datetime import datetime, timedelta

# USER MODEL
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="Student")
    profile_picture = db.Column(db.String(200), nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)
    subjects = db.relationship('Subject', backref='user', lazy=True)
    tasks = db.relationship('Task', backref='user', lazy=True)
    sessions = db.relationship('StudySession', backref='user', lazy=True)

# SUBJECT MODEL
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)
    deadline = db.Column(db.String(100))
    priority = db.Column(db.String(50))
    tasks = db.relationship('Task', backref='subject', lazy=True)

    @property
    def days_left(self):
        if not self.deadline:
            return None
        try:
            deadline_date = datetime.strptime(self.deadline, '%Y-%m-%d').date()
            today = datetime.now().date()
            return (deadline_date - today).days
        except Exception:
            return None

# TASK MODEL
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    task_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default="Pending")
    scheduled_time = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def formatted_time(self):
        if not self.scheduled_time:
            return ""
        try:
            # datetime-local is format YYYY-MM-DDTHH:MM
            dt = datetime.strptime(self.scheduled_time, '%Y-%m-%dT%H:%M')
            today = datetime.now().date()
            if dt.date() == today:
                return f"Today, {dt.strftime('%I:%M %p')}"
            elif dt.date() == today + timedelta(days=1):
                return f"Tomorrow, {dt.strftime('%I:%M %p')}"
            else:
                return dt.strftime('%b %d, %I:%M %p')
        except Exception:
            return self.scheduled_time


# STUDY SESSION MODEL
class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=25)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)