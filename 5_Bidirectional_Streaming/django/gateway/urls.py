from django.urls import path

from gateway import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("chat-batch", views.chat_batch, name="chat-batch"),
]
