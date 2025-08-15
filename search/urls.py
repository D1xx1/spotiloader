from django.urls import path
from . import views

urlpatterns = [
    path("", views.search_view, name="search"),
    path("track/<str:track_id>/", views.track_detail, name="track_detail"),
]
