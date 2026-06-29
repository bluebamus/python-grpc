from django.urls import path

from gateway import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("stream-data", views.stream_data, name="stream-data"),
]
