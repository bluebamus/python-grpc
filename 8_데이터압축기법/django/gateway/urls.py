from django.urls import path

from gateway import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("data/<str:data_id>", views.get_data, name="get_data"),
]
