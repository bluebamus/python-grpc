from django.urls import path

from gateway import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("tasks", views.submit_task, name="submit_task"),
    path("tasks/<int:task_id>", views.get_task, name="get_task"),
    path("stats", views.stats, name="stats"),
]
