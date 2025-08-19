import base64
import time
from typing import Dict, Any, List
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from djspyt import keys

# Инициализация Spotify клиента
client_credentials_manager = SpotifyClientCredentials(
    client_id=keys.SPOTIFY_CLIENT_ID,
    client_secret=keys.SPOTIFY_CLIENT_SECRET
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def search_tracks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Поиск треков через spotipy"""
    try:
        results = sp.search(q=query, type='track', limit=limit, market='US')
        items = results.get("tracks", {}).get("items", [])
        
        tracks = []
        for item in items:
            tracks.append({
                "id": item["id"],
                "name": item["name"],
                "artists": ", ".join(a["name"] for a in item.get("artists", [])),
                "album": item.get("album", {}).get("name"),
                "image": (item.get("album", {}).get("images") or [{}])[0].get("url"),
                "duration_ms": item.get("duration_ms"),
                "preview_url": item.get("preview_url"),
                "external_url": item.get("external_urls", {}).get("spotify"),
            })
        return tracks
    except Exception as e:
        print(f"Ошибка поиска треков: {e}")
        return []

def get_track_metadata(track_id: str) -> Dict[str, Any]:
    """Получение метаданных трека через spotipy"""
    try:
        track = sp.track(track_id, market='US')
        
        meta = {
            "id": track["id"],
            "name": track["name"],
            "artists": ", ".join(a["name"] for a in track.get("artists", [])),
            "album": track.get("album", {}).get("name"),
            "release_date": track.get("album", {}).get("release_date"),
            "image": (track.get("album", {}).get("images") or [{}])[0].get("url"),
            "duration_ms": track.get("duration_ms"),
            "popularity": track.get("popularity"),
            "track_number": track.get("track_number"),
            "disc_number": track.get("disc_number"),
            "explicit": track.get("explicit"),
            "preview_url": track.get("preview_url"),
            "external_url": track.get("external_urls", {}).get("spotify"),
        }
        return meta
    except Exception as e:
        print(f"Ошибка получения метаданных трека: {e}")
        raise e
