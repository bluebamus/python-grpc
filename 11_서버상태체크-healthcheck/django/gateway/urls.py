from django.urls import path

from gateway import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("health/grpc", views.health_grpc, name="health_grpc"),
]
