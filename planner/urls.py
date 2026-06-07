from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup', views.signup_page, name='signup_page'),
    path('login', views.login_page, name='login_page'),
    path('forgot-password', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>', views.reset_password, name='reset_password'),
    path('logout', views.logout_view, name='logout'),
    
    path('dashboard', views.dashboard_page, name='dashboard_page'),
    path('subjects', views.subjects_page, name='subjects_page'),
    path('tasks', views.tasks_page, name='tasks_page'),
    path('schedule', views.schedule_page, name='schedule_page'),
    path('api/calendar', views.api_calendar, name='api_calendar'),
    
    path('timer', views.timer_page, name='timer_page'),
    path('log-session', views.log_session, name='log_session'),
    path('analytics', views.analytics_page, name='analytics_page'),
    path('settings', views.settings_page, name='settings_page'),
    
    path('add-subject', views.add_subject, name='add_subject'),
    path('edit-subject/<int:id>', views.edit_subject, name='edit_subject'),
    path('delete-subject/<int:id>', views.delete_subject, name='delete_subject'),
    
    path('add-task', views.add_task, name='add_task'),
    path('edit-task/<int:id>', views.edit_task, name='edit_task'),
    path('complete-task/<int:id>', views.complete_task, name='complete_task'),
    path('delete-task/<int:id>', views.delete_task, name='delete_task'),
]
