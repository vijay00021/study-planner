from datetime import datetime, date, timedelta
from .models import Subject, Task

def inject_global(request):
    user = None
    notifications = []
    
    if request.user.is_authenticated:
        user = request.user
        
        # Deadlines
        upcoming_subjects = Subject.objects.filter(user=user).exclude(deadline='')
        for sub in upcoming_subjects:
            try:
                due_date = datetime.strptime(sub.deadline, '%Y-%m-%d')
                days_diff = (due_date - datetime.now()).days
                # Match Flask logic: 0 <= days_diff <= 3
                if 0 <= days_diff <= 3:
                    tasks_for_sub = Task.objects.filter(subject=sub, status='Pending')
                    if tasks_for_sub.exists():
                        task_names = ", ".join([t.task_name for t in tasks_for_sub])
                        message = f"{sub.subject_name} is due soon! Pending tasks: {task_names}"
                    else:
                        message = f"{sub.subject_name} is due soon!"
                    notifications.append({
                        'type': 'warning',
                        'icon': 'fa-calendar',
                        'title': 'Upcoming Deadline',
                        'message': message
                    })
            except Exception:
                pass
                
        # Upcoming Events (Scheduled Tasks)
        scheduled_tasks = Task.objects.filter(user=user, status='Pending').exclude(scheduled_time='').exclude(scheduled_time__isnull=True)
        for t in scheduled_tasks:
            notifications.append({
                'type': 'primary',
                'icon': 'fa-clock',
                'title': 'Upcoming Event',
                'message': f"Task '{t.task_name}' is scheduled for {t.scheduled_time}."
            })
                
        # Alerts
        pending_count = Task.objects.filter(user=user, status='Pending').count()
        if pending_count > 5:
            notifications.append({
                'type': 'danger',
                'icon': 'fa-triangle-exclamation',
                'title': 'High Workload',
                'message': f"You have {pending_count} pending tasks. Time to focus!"
            })
            
    return {
        'current_user': user,
        'notifications': notifications
    }
