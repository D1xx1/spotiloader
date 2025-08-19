from typing import Dict, Any, Optional
import requests
import re

def search_deezer_track(artist: str, title: str) -> Optional[Dict[str, Any]]:
    """
    Поиск трека в Deezer API для получения превью
    """
    try:
        # Формируем поисковый запрос
        query = f"{artist} {title}".replace(" ", "%20")
        url = f"https://api.deezer.com/search?q={query}&limit=1"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('data') and len(data['data']) > 0:
            track = data['data'][0]
            
            return {
                'id': track.get('id'),
                'title': track.get('title'),
                'artist': track.get('artist', {}).get('name'),
                'album': track.get('album', {}).get('title'),
                'preview_url': track.get('preview'),
                'duration': track.get('duration'),
                'link': track.get('link'),
                'cover': track.get('album', {}).get('cover_medium')
            }
        
        return None
        
    except Exception as e:
        print(f"Ошибка поиска в Deezer: {e}")
        return None

def get_deezer_preview(artist: str, title: str) -> Optional[str]:
    """
    Получение URL превью трека из Deezer
    """
    track = search_deezer_track(artist, title)
    return track.get('preview_url') if track else None

def clean_artist_name(artist: str) -> str:
    """
    Очистка имени артиста от лишних символов
    """
    # Убираем "feat.", "ft.", "featuring" и т.д.
    artist = re.sub(r'\s*(feat\.?|ft\.?|featuring)\s*.*$', '', artist, flags=re.IGNORECASE)
    # Убираем скобки и их содержимое
    artist = re.sub(r'\s*\([^)]*\)', '', artist)
    return artist.strip()

def get_enhanced_preview(spotify_artist: str, spotify_title: str) -> Optional[Dict[str, Any]]:
    """
    Улучшенный поиск превью с очисткой данных
    """
    # Очищаем имя артиста
    clean_artist = clean_artist_name(spotify_artist)
    
    # Пробуем разные варианты поиска
    search_variants = [
        (clean_artist, spotify_title),
        (spotify_artist, spotify_title),
        (clean_artist.split(',')[0], spotify_title),  # Берем первого артиста
        (clean_artist.split('&')[0], spotify_title),  # Берем первого артиста
    ]
    
    for artist, title in search_variants:
        track = search_deezer_track(artist, title)
        if track and track.get('preview_url'):
            return track
    
    return None
