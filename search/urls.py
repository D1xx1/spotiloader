from django.urls import path
from . import views

urlpatterns = [
    path("youtube/<str:video_id>/audio/", views.youtube_audio, name="youtube_audio"),
    path("", views.search_view, name="search"),
    path("track/<str:track_id>/", views.track_detail, name="track_detail"),
]
