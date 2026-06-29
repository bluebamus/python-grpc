from django.urls import path

from gateway import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("books", views.serialize_book, name="serialize_book"),
    path("orders", views.serialize_order, name="serialize_order"),
    path("books/decode", views.decode_book, name="decode_book"),
]
