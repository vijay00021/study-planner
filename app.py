from flask import Flask, render_template, request, redirect, session, url_for
from extensions import db
from models.models import User, Subject, Task
from functools import wraps
import os
import re
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, date, timedelta

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key_123")
app.config['SECRET_KEY'] = app.secret_key
app.permanent_session_lifetime = timedelta(days=30)

# Validation Helpers
def is_valid_email(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def is_strong_password(password):
    # Min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    if not any(not c.isalnum() for c in password):
        return False, "Password must contain at least one special character (e.g. !@#$%^&*)."
    return True, ""

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/studyplanner")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_global():
    user = None
    notifications = []
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        
        if user:
            from datetime import datetime
            
            # Deadlines
            upcoming_subjects = Subject.query.filter_by(user_id=user.id).filter(Subject.deadline != '').all()
            for sub in upcoming_subjects:
                try:
                    due_date = datetime.strptime(sub.deadline, '%Y-%m-%d')
                    if 0 <= (due_date - datetime.now()).days <= 3:
                        tasks_for_sub = Task.query.filter_by(subject_id=sub.id, status='Pending').all()
                        if tasks_for_sub:
                            task_names = ", ".join([t.task_name for t in tasks_for_sub])
                            message = f"{sub.subject_name} is due soon! Pending tasks: {task_names}"
                        else:
                            message = f"{sub.subject_name} is due soon!"
                        notifications.append({'type': 'warning', 'icon': 'fa-calendar', 'title': 'Upcoming Deadline', 'message': message})
                except:
                    pass
                    
            # Upcoming Events (Scheduled Tasks)
            scheduled_tasks = Task.query.filter_by(user_id=user.id, status='Pending').filter(Task.scheduled_time != '').filter(Task.scheduled_time.isnot(None)).all()
            for t in scheduled_tasks:
                notifications.append({'type': 'primary', 'icon': 'fa-clock', 'title': 'Upcoming Event', 'message': f"Task '{t.task_name}' is scheduled for {t.scheduled_time}."})
                    
            # Alerts
            pending_count = Task.query.filter_by(user_id=user.id, status='Pending').count()
            if pending_count > 5:
                notifications.append({'type': 'danger', 'icon': 'fa-triangle-exclamation', 'title': 'High Workload', 'message': f"You have {pending_count} pending tasks. Time to focus!"})
        else:
            session.pop('user_id', None)

    return dict(current_user=user, notifications=notifications)

# --- AUTH ROUTES ---

@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    error = None
    form_data = {}
    if request.method == 'POST':
        form_data['username'] = request.form.get('username', '')
        form_data['email'] = request.form.get('email', '')
        form_data['password'] = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if form_data['password'] != confirm_password:
            error = "Passwords do not match."
        elif not is_valid_email(form_data['email']):
            error = "Please enter a valid email address."
        elif User.query.filter_by(email=form_data['email']).first():
            error = "Email already registered."
        elif User.query.filter_by(username=form_data['username']).first():
            error = "Username already taken. Please choose another."
        else:
            is_strong, msg = is_strong_password(form_data['password'])
            if not is_strong:
                error = msg
            else:
                hashed_password = generate_password_hash(form_data['password'])
                new_user = User(username=form_data['username'], email=form_data['email'], password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for('login_page'))
    return render_template('signup.html', error=error, form_data=form_data)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    email = ''
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        remember = request.form.get('remember')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            if remember:
                session.permanent = True
            return redirect(url_for('home'))
        return render_template('login.html', error="Invalid Email or Password", email=email)
    return render_template('login.html', email=email)

import uuid

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    message = None
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = str(uuid.uuid4())
            user.reset_token = token
            db.session.commit()
            reset_url = url_for('reset_password', token=token, _external=True)
            message = f"For this demo, we've generated your reset link here: {reset_url}"
        else:
            message = "If an account with that email exists, a reset link was sent."
    return render_template('forgot_password.html', message=message)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        return "Invalid or expired token.", 400
        
    if request.method == 'POST':
        new_password = request.form['password']
        user.password = generate_password_hash(new_password)
        user.reset_token = None
        db.session.commit()
        return redirect(url_for('login_page'))
    return render_template('reset_password.html', token=token)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# --- DASHBOARD & SIDEBAR ROUTES ---

@app.route('/')
def home():
    if 'user_id' in session:
        user_id = session['user_id']
        subjects = Subject.query.filter_by(user_id=user_id).all()
        tasks = Task.query.filter_by(user_id=user_id).order_by(Task.status.desc(), Task.created_at.desc()).limit(10).all()
        all_tasks = Task.query.filter_by(user_id=user_id).all()
        
        total_subjects = len(subjects)
        pending_tasks = Task.query.filter_by(user_id=user_id, status="Pending").count()
        completed_tasks = Task.query.filter_by(user_id=user_id, status="Completed").count()
        
        study_hours = completed_tasks * 2 # Mock data for UI

        return render_template('index.html', subjects=subjects, tasks=tasks, all_tasks=all_tasks,
                               total_subjects=total_subjects, pending_tasks=pending_tasks, 
                               completed_tasks=completed_tasks, study_hours=study_hours, active_page='dashboard')
    else:
        # Serve landing page with mock data for guest view
        class MockSubject:
            def __init__(self, id, name, deadline, priority, days_left):
                self.id = id
                self.subject_name = name
                self.deadline = deadline
                self.priority = priority
                self.days_left = days_left
                self.tasks = []

        class MockTask:
            def __init__(self, id, name, subject, status, scheduled_time):
                self.id = id
                self.task_name = name
                self.subject = subject
                self.subject_id = subject.id if subject else None
                self.status = status
                self.scheduled_time = scheduled_time

            @property
            def formatted_time(self):
                if not self.scheduled_time:
                    return ""
                try:
                    dt = datetime.strptime(self.scheduled_time, '%Y-%m-%dT%H:%M')
                    today_date = date.today()
                    if dt.date() == today_date:
                        return f"Today, {dt.strftime('%I:%M %p')}"
                    elif dt.date() == today_date + timedelta(days=1):
                        return f"Tomorrow, {dt.strftime('%I:%M %p')}"
                    else:
                        return dt.strftime('%b %d, %I:%M %p')
                except Exception:
                    return self.scheduled_time

        s1 = MockSubject(1, "Mathematics", (date.today() + timedelta(days=3)).strftime('%Y-%m-%d'), "High", 3)
        s2 = MockSubject(2, "Computer Science", (date.today() + timedelta(days=6)).strftime('%Y-%m-%d'), "Medium", 6)
        s3 = MockSubject(3, "Physics", (date.today() + timedelta(days=2)).strftime('%Y-%m-%d'), "High", 2)
        s4 = MockSubject(4, "Chemistry", (date.today() + timedelta(days=11)).strftime('%Y-%m-%d'), "Low", 11)

        today_str = date.today().strftime('%Y-%m-%d')
        tomorrow_str = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')

        t1 = MockTask(1, "Solve Calculus exercises", s1, "Pending", f"{today_str}T10:00")
        t2 = MockTask(2, "Implement binary search tree", s2, "Completed", f"{today_str}T14:30")
        t3 = MockTask(3, "Review thermodynamics notes", s3, "Pending", f"{today_str}T16:00")
        t4 = MockTask(4, "Lab report preparation", s4, "Pending", f"{tomorrow_str}T09:00")
        t5 = MockTask(5, "Prepare presentation slides", s2, "Completed", f"{today_str}T13:00")

        s1.tasks.append(t1)
        s2.tasks.extend([t2, t5])
        s3.tasks.append(t3)
        s4.tasks.append(t4)

        subjects = [s1, s2, s3, s4]
        tasks = [t1, t2, t3, t4, t5]

        total_subjects = len(subjects)
        pending_tasks = sum(1 for t in tasks if t.status == "Pending")
        completed_tasks = sum(1 for t in tasks if t.status == "Completed")
        study_hours = 24

        return render_template('landing.html', subjects=subjects, tasks=tasks, all_tasks=tasks,
                               total_subjects=total_subjects, pending_tasks=pending_tasks,
                               completed_tasks=completed_tasks, study_hours=study_hours, active_page='home')

@app.route('/dashboard')
def dashboard_page():
    if 'user_id' in session:
        return redirect(url_for('home'))

    class MockSubject:
        def __init__(self, id, name, deadline, priority, days_left):
            self.id = id
            self.subject_name = name
            self.deadline = deadline
            self.priority = priority
            self.days_left = days_left
            self.tasks = []

    class MockTask:
        def __init__(self, id, name, subject, status, scheduled_time):
            self.id = id
            self.task_name = name
            self.subject = subject
            self.subject_id = subject.id if subject else None
            self.status = status
            self.scheduled_time = scheduled_time

        @property
        def formatted_time(self):
            if not self.scheduled_time:
                return ""
            try:
                dt = datetime.strptime(self.scheduled_time, '%Y-%m-%dT%H:%M')
                today_date = date.today()
                if dt.date() == today_date:
                    return f"Today, {dt.strftime('%I:%M %p')}"
                elif dt.date() == today_date + timedelta(days=1):
                    return f"Tomorrow, {dt.strftime('%I:%M %p')}"
                else:
                    return dt.strftime('%b %d, %I:%M %p')
            except Exception:
                return self.scheduled_time

    s1 = MockSubject(1, "Mathematics", (date.today() + timedelta(days=3)).strftime('%Y-%m-%d'), "High", 3)
    s2 = MockSubject(2, "Computer Science", (date.today() + timedelta(days=6)).strftime('%Y-%m-%d'), "Medium", 6)
    s3 = MockSubject(3, "Physics", (date.today() + timedelta(days=2)).strftime('%Y-%m-%d'), "High", 2)
    s4 = MockSubject(4, "Chemistry", (date.today() + timedelta(days=11)).strftime('%Y-%m-%d'), "Low", 11)

    today_str = date.today().strftime('%Y-%m-%d')
    tomorrow_str = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')

    t1 = MockTask(1, "Solve Calculus exercises", s1, "Pending", f"{today_str}T10:00")
    t2 = MockTask(2, "Implement binary search tree", s2, "Completed", f"{today_str}T14:30")
    t3 = MockTask(3, "Review thermodynamics notes", s3, "Pending", f"{today_str}T16:00")
    t4 = MockTask(4, "Lab report preparation", s4, "Pending", f"{tomorrow_str}T09:00")
    t5 = MockTask(5, "Prepare presentation slides", s2, "Completed", f"{today_str}T13:00")

    s1.tasks.append(t1)
    s2.tasks.extend([t2, t5])
    s3.tasks.append(t3)
    s4.tasks.append(t4)

    subjects = [s1, s2, s3, s4]
    tasks = [t1, t2, t3, t4, t5]

    total_subjects = len(subjects)
    pending_tasks = sum(1 for t in tasks if t.status == "Pending")
    completed_tasks = sum(1 for t in tasks if t.status == "Completed")
    study_hours = 24

    return render_template('index.html', subjects=subjects, tasks=tasks, all_tasks=tasks,
                           total_subjects=total_subjects, pending_tasks=pending_tasks,
                           completed_tasks=completed_tasks, study_hours=study_hours, active_page='dashboard')


@app.route('/subjects')
@login_required
def subjects_page():
    user_id = session['user_id']
    subjects = Subject.query.filter_by(user_id=user_id).all()
    return render_template('subjects.html', subjects=subjects, active_page='subjects')

@app.route('/tasks')
@login_required
def tasks_page():
    user_id = session['user_id']
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.status.desc(), Task.created_at.desc()).all()
    subjects = Subject.query.filter_by(user_id=user_id).all()
    return render_template('tasks.html', tasks=tasks, subjects=subjects, active_page='tasks')

@app.route('/schedule')
@login_required
def schedule_page():
    user_id = session['user_id']
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.scheduled_time).all()
    return render_template('schedule.html', tasks=tasks, active_page='schedule')

from flask import jsonify

@app.route('/api/calendar')
def api_calendar():
    if 'user_id' not in session:
        from datetime import date, timedelta
        today = date.today()
        events = [
            {
                'title': 'Solve Calculus exercises',
                'start': today.strftime('%Y-%m-%d') + 'T10:00:00',
                'backgroundColor': '#f59e0b',
                'borderColor': 'transparent'
            },
            {
                'title': 'Implement binary tree',
                'start': today.strftime('%Y-%m-%d') + 'T14:30:00',
                'backgroundColor': '#10b981',
                'borderColor': 'transparent'
            },
            {
                'title': 'Physics Due',
                'start': (today + timedelta(days=2)).strftime('%Y-%m-%d'),
                'backgroundColor': '#ef4444',
                'borderColor': 'transparent',
                'allDay': True
            },
            {
                'title': 'Mathematics Due',
                'start': (today + timedelta(days=3)).strftime('%Y-%m-%d'),
                'backgroundColor': '#ef4444',
                'borderColor': 'transparent',
                'allDay': True
            }
        ]
        return jsonify(events)

    user_id = session['user_id']
    events = []
    
    tasks = Task.query.filter_by(user_id=user_id).filter(Task.scheduled_time != '').filter(Task.scheduled_time.isnot(None)).all()
    for t in tasks:
        events.append({
            'title': t.task_name,
            'start': t.scheduled_time,
            'backgroundColor': '#10b981' if t.status == 'Completed' else '#f59e0b',
            'borderColor': 'transparent',
            'url': url_for('tasks_page')
        })
        
    subjects = Subject.query.filter_by(user_id=user_id).filter(Subject.deadline != '').all()
    for s in subjects:
        events.append({
            'title': f"{s.subject_name} Due",
            'start': s.deadline,
            'backgroundColor': '#ef4444',
            'borderColor': 'transparent',
            'allDay': True
        })
        
    return jsonify(events)

from models.models import StudySession
from datetime import date

@app.route('/timer')
@login_required
def timer_page():
    return render_template('timer.html', active_page='timer')

@app.route('/log-session', methods=['POST'])
@login_required
def log_session():
    duration = int(request.form.get('duration', 25))
    today_str = date.today().strftime('%Y-%m-%d')
    new_session = StudySession(user_id=session['user_id'], date=today_str, duration_minutes=duration)
    db.session.add(new_session)
    db.session.commit()
    return redirect(url_for('analytics_page'))

from datetime import timedelta

@app.route('/analytics')
@login_required
def analytics_page():
    user_id = session['user_id']
    today = date.today()
    labels = []
    data = []
    
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')
        labels.append(target_date.strftime('%a'))
        
        sessions = StudySession.query.filter_by(user_id=user_id, date=date_str).all()
        total_mins = sum(s.duration_minutes for s in sessions)
        data.append(round(total_mins / 60, 1))
        
    return render_template('analytics.html', active_page='analytics', chart_labels=labels, chart_data=data)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    error = None
    success = None
    pwd_error = None
    pwd_success = None
    
    if request.method == 'POST':
        user = User.query.get(session['user_id'])
        
        # Handle Password Change
        if 'current_password' in request.form:
            current_pwd = request.form['current_password']
            new_pwd = request.form['new_password']
            confirm_pwd = request.form['confirm_password']
            
            if not check_password_hash(user.password, current_pwd):
                pwd_error = "Current password is incorrect."
            elif new_pwd != confirm_pwd:
                pwd_error = "New passwords do not match."
            else:
                is_strong, msg = is_strong_password(new_pwd)
                if not is_strong:
                    pwd_error = msg
                else:
                    user.password = generate_password_hash(new_pwd)
                    db.session.commit()
                    pwd_success = "Password updated successfully!"
                
        # Handle Profile Picture Upload
        elif 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                user.profile_picture = f"uploads/{filename}"
                db.session.commit()
                success = "Profile picture updated successfully!"
                
        # Handle Profile Info Update
        elif 'username' in request.form and 'email' in request.form:
            new_username = request.form['username']
            new_email = request.form['email']
            existing_user = User.query.filter((User.username == new_username) | (User.email == new_email)).first()
            if existing_user and existing_user.id != user.id:
                error = "Username or Email already exists for another user."
            else:
                user.username = new_username
                user.email = new_email
                db.session.commit()
                session['username'] = new_username
                success = "Profile details updated successfully."
                
    return render_template('settings.html', active_page='settings', error=error, success=success, pwd_error=pwd_error, pwd_success=pwd_success)

# --- ACTION ROUTES ---

@app.route('/add-subject', methods=['POST'])
@login_required
def add_subject():
    subject_name = request.form['subject_name']
    deadline = request.form.get('deadline', '')
    priority = request.form.get('priority', 'Medium')
    
    if deadline:
        try:
            deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
            if deadline_date < date.today():
                return redirect((request.referrer or url_for('home')) + "?error=Deadline+cannot+be+in+the+past")
        except ValueError:
            pass

    new_subject = Subject(user_id=session['user_id'], subject_name=subject_name, deadline=deadline, priority=priority)
    db.session.add(new_subject)
    db.session.commit()
    return redirect(request.referrer or url_for('home'))

@app.route('/edit-subject/<int:id>', methods=['POST'])
@login_required
def edit_subject(id):
    subject = Subject.query.filter_by(id=id, user_id=session['user_id']).first()
    if subject:
        deadline = request.form.get('deadline', '')
        if deadline:
            try:
                deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                if deadline_date < date.today():
                    return redirect((request.referrer or url_for('subjects_page')) + "?error=Deadline+cannot+be+in+the+past")
            except ValueError:
                pass
        subject.subject_name = request.form.get('subject_name', subject.subject_name)
        subject.deadline = deadline
        subject.priority = request.form.get('priority', subject.priority)
        db.session.commit()
    return redirect(request.referrer or url_for('subjects_page'))

@app.route('/delete-subject/<int:id>')
@login_required
def delete_subject(id):
    subject = Subject.query.filter_by(id=id, user_id=session['user_id']).first()
    if subject:
        Task.query.filter_by(subject_id=id).delete()
        db.session.delete(subject)
        db.session.commit()
    return redirect(request.referrer or url_for('home'))

@app.route('/add-task', methods=['POST'])
@login_required
def add_task():
    task_name = request.form['task_name']
    subject_id = request.form.get('subject_id')
    if subject_id == '': subject_id = None
    scheduled_time = request.form.get('scheduled_time', '')
    
    if scheduled_time:
        try:
            scheduled_dt = datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
            if scheduled_dt.date() < date.today():
                return redirect((request.referrer or url_for('home')) + "?error=Scheduled+date+cannot+be+in+the+past")
        except ValueError:
            try:
                scheduled_date = datetime.strptime(scheduled_time, '%Y-%m-%d').date()
                if scheduled_date < date.today():
                    return redirect((request.referrer or url_for('home')) + "?error=Scheduled+date+cannot+be+in+the+past")
            except ValueError:
                pass

    description = request.form.get('description', '')
    new_task = Task(user_id=session['user_id'], task_name=task_name, subject_id=subject_id, scheduled_time=scheduled_time, description=description)
    db.session.add(new_task)
    db.session.commit()
    return redirect(request.referrer or url_for('home'))

@app.route('/edit-task/<int:id>', methods=['POST'])
@login_required
def edit_task(id):
    task = Task.query.filter_by(id=id, user_id=session['user_id']).first()
    if task:
        scheduled_time = request.form.get('scheduled_time', '')
        if scheduled_time:
            try:
                scheduled_dt = datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
                if scheduled_dt.date() < date.today():
                    return redirect((request.referrer or url_for('home')) + "?error=Scheduled+date+cannot+be+in+the+past")
            except ValueError:
                try:
                    scheduled_date = datetime.strptime(scheduled_time, '%Y-%m-%d').date()
                    if scheduled_date < date.today():
                        return redirect((request.referrer or url_for('home')) + "?error=Scheduled+date+cannot+be+in+the+past")
                except ValueError:
                    pass
        task.task_name = request.form.get('task_name', task.task_name)
        subject_id = request.form.get('subject_id')
        task.subject_id = subject_id if subject_id != '' else None
        task.scheduled_time = scheduled_time
        task.description = request.form.get('description', '')
        db.session.commit()
    return redirect(request.referrer or url_for('home'))

@app.route('/complete-task/<int:id>')
@login_required
def complete_task(id):
    task = Task.query.filter_by(id=id, user_id=session['user_id']).first()
    if task:
        task.status = "Completed" if task.status == "Pending" else "Pending"
        db.session.commit()
    return redirect(request.referrer or url_for('home'))

@app.route('/delete-task/<int:id>')
@login_required
def delete_task(id):
    task = Task.query.filter_by(id=id, user_id=session['user_id']).first()
    if task:
        db.session.delete(task)
        db.session.commit()
    return redirect(request.referrer or url_for('home'))

if __name__ == "__main__":
    app.run()