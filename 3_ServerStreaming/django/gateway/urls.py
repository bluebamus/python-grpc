from django.urls import path

from gateway import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("chat-stream", views.chat_stream, name="chat_stream"),
]
