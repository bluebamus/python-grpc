from django.urls import path

from gateway import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("operation", views.operation, name="operation"),
]
