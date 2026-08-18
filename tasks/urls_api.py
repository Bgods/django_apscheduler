from django.urls import path
from . import views

app_name = 'tasks_api'

urlpatterns = [
    path('tasks/<int:pk>/execute/', views.api_execute_task, name='api_execute_task'),
]
