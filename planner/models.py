from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import datetime, date, timedelta

# USER MODEL
class User(AbstractUser):
    role = models.CharField(max_length=50, default="Student")
    profile_picture = models.CharField(max_length=200, null=True, blank=True)
    reset_token = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(unique=True)

    @property
    def has_document_avatar(self):
        if not self.profile_picture:
            return False
        return any(self.profile_picture.endswith(ext) for ext in ['.pdf', '.doc', '.docx'])

    def __str__(self):
        return self.username

# SUBJECT MODEL
class Subject(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    subject_name = models.CharField(max_length=100)
    deadline = models.CharField(max_length=100, null=True, blank=True)
    priority = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.subject_name} ({self.user.username})"

    @property
    def days_left(self):
        if not self.deadline:
            return None
        try:
            deadline_date = datetime.strptime(self.deadline, '%Y-%m-%d').date()
            today = date.today()
            return (deadline_date - today).days
        except Exception:
            return None

    @property
    def completion_percentage(self):
        total = self.tasks.count()
        if total == 0:
            return 0
        completed = self.tasks.filter(status='Completed').count()
        return int(completed / total * 100)

    @property
    def is_due_soon(self):
        days = self.days_left
        return days is not None and 0 <= days <= 7

# TASK MODEL
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    task_name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default="Pending")
    scheduled_time = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.task_name

    @property
    def formatted_time(self):
        if not self.scheduled_time:
            return ""
        try:
            # datetime-local is format YYYY-MM-DDTHH:MM
            dt = datetime.strptime(self.scheduled_time, '%Y-%m-%dT%H:%M')
            today = date.today()
            if dt.date() == today:
                return f"Today, {dt.strftime('%I:%M %p')}"
            elif dt.date() == today + timedelta(days=1):
                return f"Tomorrow, {dt.strftime('%I:%M %p')}"
            else:
                return dt.strftime('%b %d, %I:%M %p')
        except Exception:
            return self.scheduled_time

# STUDY SESSION MODEL
class StudySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    date = models.CharField(max_length=50)
    duration_minutes = models.IntegerField(default=25)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.duration_minutes}m)"
