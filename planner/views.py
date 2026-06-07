import os
import uuid
import re
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.conf import settings
from django.utils.text import get_valid_filename

from .models import User, Subject, Task, StudySession

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

# --- AUTH VIEWS ---

def signup_page(request):
    error = None
    form_data = {}
    if request.method == 'POST':
        form_data['username'] = request.POST.get('username', '')
        form_data['email'] = request.POST.get('email', '')
        form_data['password'] = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if form_data['password'] != confirm_password:
            error = "Passwords do not match."
        elif not is_valid_email(form_data['email']):
            error = "Please enter a valid email address."
        elif User.objects.filter(email=form_data['email']).exists():
            error = "Email already registered."
        elif User.objects.filter(username=form_data['username']).exists():
            error = "Username already taken. Please choose another."
        else:
            is_strong, msg = is_strong_password(form_data['password'])
            if not is_strong:
                error = msg
            else:
                new_user = User.objects.create_user(
                    username=form_data['username'],
                    email=form_data['email'],
                    password=form_data['password'],
                    role="Student"
                )
                return redirect('login_page')
    return render(request, 'signup.html', {'error': error, 'form_data': form_data})

def login_page(request):
    email = ''
    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        remember = request.POST.get('remember')
        
        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
            login(request, user)
            if remember:
                request.session.set_expiry(30 * 24 * 3600)  # 30 days
            else:
                request.session.set_expiry(0)  # expires on browser close
            return redirect('home')
        error = "Invalid Email or Password"
    return render(request, 'login.html', {'email': email, 'error': error})

def forgot_password(request):
    message = None
    if request.method == 'POST':
        email = request.POST.get('email', '')
        user = User.objects.filter(email=email).first()
        if user:
            token = str(uuid.uuid4())
            user.reset_token = token
            user.save()
            reset_url = request.build_absolute_uri(reverse('reset_password', args=[token]))
            message = f"For this demo, we've generated your reset link here: {reset_url}"
        else:
            message = "If an account with that email exists, a reset link was sent."
    return render(request, 'forgot_password.html', {'message': message})

def reset_password(request, token):
    user = User.objects.filter(reset_token=token).first()
    if not user:
        return HttpResponse("Invalid or expired token.", status=400)
        
    if request.method == 'POST':
        new_password = request.POST.get('password', '')
        user.set_password(new_password)
        user.reset_token = None
        user.save()
        return redirect('login_page')
    return render(request, 'reset_password.html', {'token': token})

def logout_view(request):
    logout(request)
    return redirect('login_page')

# --- DASHBOARD & SIDEBAR VIEWS ---

def home(request):
    if request.user.is_authenticated:
        user = request.user
        subjects = Subject.objects.filter(user=user)
        tasks = Task.objects.filter(user=user).order_by('status', '-created_at')[:10]
        all_tasks = Task.objects.filter(user=user)
        
        total_subjects = subjects.count()
        pending_tasks = Task.objects.filter(user=user, status="Pending").count()
        completed_tasks = Task.objects.filter(user=user, status="Completed").count()
        study_hours = completed_tasks * 2 # Mock data for UI
        
        return render(request, 'index.html', {
            'subjects': subjects,
            'tasks': tasks,
            'all_tasks': all_tasks,
            'total_subjects': total_subjects,
            'pending_tasks': pending_tasks,
            'completed_tasks': completed_tasks,
            'study_hours': study_hours,
            'active_page': 'dashboard'
        })
    else:
        # Mock Guest data
        class MockSubject:
            def __init__(self, id, name, deadline, priority, days_left):
                self.id = id
                self.subject_name = name
                self.deadline = deadline
                self.priority = priority
                self.days_left = days_left
                self.tasks = []

            @property
            def completion_percentage(self):
                total = len(self.tasks)
                if total == 0:
                    return 0
                completed = sum(1 for t in self.tasks if t.status == 'Completed')
                return int(completed / total * 100)

            @property
            def is_due_soon(self):
                days = self.days_left
                return days is not None and 0 <= days <= 7

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

        return render(request, 'landing.html', {
            'subjects': subjects,
            'tasks': tasks,
            'all_tasks': tasks,
            'total_subjects': total_subjects,
            'pending_tasks': pending_tasks,
            'completed_tasks': completed_tasks,
            'study_hours': study_hours,
            'active_page': 'home'
        })

def dashboard_page(request):
    if request.user.is_authenticated:
        return redirect('home')

    class MockSubject:
        def __init__(self, id, name, deadline, priority, days_left):
            self.id = id
            self.subject_name = name
            self.deadline = deadline
            self.priority = priority
            self.days_left = days_left
            self.tasks = []

        @property
        def completion_percentage(self):
            total = len(self.tasks)
            if total == 0:
                return 0
            completed = sum(1 for t in self.tasks if t.status == 'Completed')
            return int(completed / total * 100)

        @property
        def is_due_soon(self):
            days = self.days_left
            return days is not None and 0 <= days <= 7

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

    return render(request, 'index.html', {
        'subjects': subjects,
        'tasks': tasks,
        'all_tasks': tasks,
        'total_subjects': total_subjects,
        'pending_tasks': pending_tasks,
        'completed_tasks': completed_tasks,
        'study_hours': study_hours,
        'active_page': 'dashboard'
    })

@login_required
def subjects_page(request):
    subjects = Subject.objects.filter(user=request.user)
    return render(request, 'subjects.html', {'subjects': subjects, 'active_page': 'subjects'})

@login_required
def tasks_page(request):
    tasks = Task.objects.filter(user=request.user).order_by('status', '-created_at')
    subjects = Subject.objects.filter(user=request.user)
    return render(request, 'tasks.html', {'tasks': tasks, 'subjects': subjects, 'active_page': 'tasks'})

@login_required
def schedule_page(request):
    tasks = Task.objects.filter(user=request.user).order_by('scheduled_time')
    return render(request, 'schedule.html', {'tasks': tasks, 'active_page': 'schedule'})

def api_calendar(request):
    if not request.user.is_authenticated:
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
        return JsonResponse(events, safe=False)

    user = request.user
    events = []
    
    tasks = Task.objects.filter(user=user).exclude(scheduled_time='').exclude(scheduled_time__isnull=True)
    for t in tasks:
        events.append({
            'title': t.task_name,
            'start': t.scheduled_time,
            'backgroundColor': '#10b981' if t.status == 'Completed' else '#f59e0b',
            'borderColor': 'transparent',
            'url': reverse('tasks_page')
        })
        
    subjects = Subject.objects.filter(user=user).exclude(deadline='')
    for s in subjects:
        events.append({
            'title': f"{s.subject_name} Due",
            'start': s.deadline,
            'backgroundColor': '#ef4444',
            'borderColor': 'transparent',
            'allDay': True
        })
        
    return JsonResponse(events, safe=False)

@login_required
def timer_page(request):
    return render(request, 'timer.html', {'active_page': 'timer'})

@login_required
def log_session(request):
    if request.method == 'POST':
        duration = int(request.POST.get('duration', 25))
        today_str = date.today().strftime('%Y-%m-%d')
        new_session = StudySession(user=request.user, date=today_str, duration_minutes=duration)
        new_session.save()
    return redirect('analytics_page')

@login_required
def analytics_page(request):
    import json
    user = request.user
    today = date.today()
    labels = []
    data = []
    
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')
        labels.append(target_date.strftime('%a'))
        
        sessions = StudySession.objects.filter(user=user, date=date_str)
        total_mins = sum(s.duration_minutes for s in sessions)
        data.append(round(total_mins / 60, 1))
        
    return render(request, 'analytics.html', {
        'active_page': 'analytics',
        'chart_labels': json.dumps(labels),
        'chart_data': json.dumps(data)
    })

@login_required
def settings_page(request):
    error = None
    success = None
    pwd_error = None
    pwd_success = None
    user = request.user
    
    if request.method == 'POST':
        # Handle Password Change
        if 'current_password' in request.POST:
            current_pwd = request.POST.get('current_password', '')
            new_pwd = request.POST.get('new_password', '')
            confirm_pwd = request.POST.get('confirm_password', '')
            
            if not user.check_password(current_pwd):
                pwd_error = "Current password is incorrect."
            elif new_pwd != confirm_pwd:
                pwd_error = "New passwords do not match."
            else:
                is_strong, msg = is_strong_password(new_pwd)
                if not is_strong:
                    pwd_error = msg
                else:
                    user.set_password(new_pwd)
                    user.save()
                    login(request, user)  # Keep user logged in after password change
                    pwd_success = "Password updated successfully!"
                
        # Handle Profile Picture Upload
        elif 'profile_picture' in request.FILES:
            file = request.FILES['profile_picture']
            if file.name != '':
                filename = get_valid_filename(file.name)
                # Create directory in static
                upload_dir = os.path.join(settings.BASE_DIR, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, filename)
                
                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                        
                user.profile_picture = f"uploads/{filename}"
                user.save()
                success = "Profile picture updated successfully!"
                
        # Handle Profile Info Update
        elif 'username' in request.POST and 'email' in request.POST:
            new_username = request.POST.get('username', '')
            new_email = request.POST.get('email', '')
            existing_user = User.objects.filter(username=new_username).exclude(id=user.id).first()
            existing_email = User.objects.filter(email=new_email).exclude(id=user.id).first()
            
            if existing_user or existing_email:
                error = "Username or Email already exists for another user."
            else:
                user.username = new_username
                user.email = new_email
                user.save()
                success = "Profile details updated successfully."
                
    return render(request, 'settings.html', {
        'active_page': 'settings',
        'error': error,
        'success': success,
        'pwd_error': pwd_error,
        'pwd_success': pwd_success
    })

# --- ACTION VIEWS ---

@login_required
def add_subject(request):
    if request.method == 'POST':
        subject_name = request.POST.get('subject_name', '')
        deadline = request.POST.get('deadline', '')
        priority = request.POST.get('priority', 'Medium')
        
        if deadline:
            try:
                deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                if deadline_date < date.today():
                    return redirect((request.META.get('HTTP_REFERER') or reverse('home')) + "?error=Deadline+cannot+be+in+the+past")
            except ValueError:
                pass

        new_subject = Subject(user=request.user, subject_name=subject_name, deadline=deadline, priority=priority)
        new_subject.save()
    return redirect(request.META.get('HTTP_REFERER') or reverse('home'))

@login_required
def edit_subject(request, id):
    if request.method == 'POST':
        subject = Subject.objects.filter(id=id, user=request.user).first()
        if subject:
            deadline = request.POST.get('deadline', '')
            if deadline:
                try:
                    deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                    if deadline_date < date.today():
                        return redirect((request.META.get('HTTP_REFERER') or reverse('subjects_page')) + "?error=Deadline+cannot+be+in+the+past")
                except ValueError:
                    pass
            subject.subject_name = request.POST.get('subject_name', subject.subject_name)
            subject.deadline = deadline
            subject.priority = request.POST.get('priority', subject.priority)
            subject.save()
    return redirect(request.META.get('HTTP_REFERER') or reverse('subjects_page'))

@login_required
def delete_subject(request, id):
    subject = Subject.objects.filter(id=id, user=request.user).first()
    if subject:
        # Cascade tasks deletion is handled by models.CASCADE in ForeignKey!
        subject.delete()
    return redirect(request.META.get('HTTP_REFERER') or reverse('home'))

@login_required
def add_task(request):
    if request.method == 'POST':
        task_name = request.POST.get('task_name', '')
        subject_id = request.POST.get('subject_id')
        if subject_id == '':
            subject_id = None
        scheduled_time = request.POST.get('scheduled_time', '')
        
        if scheduled_time:
            try:
                scheduled_dt = datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
                if scheduled_dt.date() < date.today():
                    return redirect((request.META.get('HTTP_REFERER') or reverse('home')) + "?error=Scheduled+date+cannot+be+in+the+past")
            except ValueError:
                try:
                    scheduled_date = datetime.strptime(scheduled_time, '%Y-%m-%d').date()
                    if scheduled_date < date.today():
                        return redirect((request.META.get('HTTP_REFERER') or reverse('home')) + "?error=Scheduled+date+cannot+be+in+the+past")
                except ValueError:
                    pass

        description = request.POST.get('description', '')
        subject = Subject.objects.filter(id=subject_id, user=request.user).first() if subject_id else None
        new_task = Task(user=request.user, subject=subject, task_name=task_name, scheduled_time=scheduled_time, description=description)
        new_task.save()
    return redirect(request.META.get('HTTP_REFERER') or reverse('home'))

@login_required
def edit_task(request, id):
    if request.method == 'POST':
        task = Task.objects.filter(id=id, user=request.user).first()
        if task:
            scheduled_time = request.POST.get('scheduled_time', '')
            if scheduled_time:
                try:
                    scheduled_dt = datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
                    if scheduled_dt.date() < date.today():
                        return redirect((request.META.get('HTTP_REFERER') or reverse('home')) + "?error=Scheduled+date+cannot+be+in+the+past")
                except ValueError:
                    try:
                        scheduled_date = datetime.strptime(scheduled_time, '%Y-%m-%d').date()
                        if scheduled_date < date.today():
                            return redirect((request.META.get('HTTP_REFERER') or reverse('home')) + "?error=Scheduled+date+cannot+be+in+the+past")
                    except ValueError:
                        pass
            task.task_name = request.POST.get('task_name', task.task_name)
            subject_id = request.POST.get('subject_id')
            task.subject = Subject.objects.filter(id=subject_id, user=request.user).first() if subject_id else None
            task.scheduled_time = scheduled_time
            task.description = request.POST.get('description', '')
            task.save()
    return redirect(request.META.get('HTTP_REFERER') or reverse('home'))

@login_required
def complete_task(request, id):
    task = Task.objects.filter(id=id, user=request.user).first()
    if task:
        task.status = "Completed" if task.status == "Pending" else "Pending"
        task.save()
    return redirect(request.META.get('HTTP_REFERER') or reverse('home'))

@login_required
def delete_task(request, id):
    task = Task.objects.filter(id=id, user=request.user).first()
    if task:
        task.delete()
    return redirect(request.META.get('HTTP_REFERER') or reverse('home'))
