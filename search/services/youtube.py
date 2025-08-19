from typing import Dict, Any, List
import requests
import re
from djspyt import keys

def clean_query(query: str) -> str:
    """Очищает запрос от специальных символов и лишних пробелов"""
    # Убираем специальные символы, оставляем буквы, цифры, пробелы и дефисы
    cleaned = re.sub(r'[^\w\s\-]', ' ', query)
    # Убираем лишние пробелы
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def search_youtube(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    """Поиск на YouTube с несколькими стратегиями для сложных запросов"""
    
    # Стратегия 1: Оригинальный запрос
    results = _search_youtube_single(query, limit)
    if results:
        return results
    
    # Стратегия 2: Очищенный запрос (без специальных символов)
    cleaned_query = clean_query(query)
    if cleaned_query != query:
        results = _search_youtube_single(cleaned_query, limit)
        if results:
            return results
    
    # Стратегия 3: Поиск только по названию трека (если есть артист)
    if ' - ' in query:
        track_name = query.split(' - ')[-1].strip()
        if track_name and track_name != query:
            results = _search_youtube_single(track_name, limit)
            if results:
                return results
    
    # Стратегия 4: Поиск только по артисту (если есть артист)
    if ' - ' in query:
        artist = query.split(' - ')[0].strip()
        if artist and artist != query:
            results = _search_youtube_single(artist, limit)
            if results:
                return results
    
    return []

def _search_youtube_single(query: str, limit: int) -> List[Dict[str, Any]]:
    """Выполняет один поисковый запрос к YouTube API"""
    params = {
        "part": "snippet",
        "q": query,
        "maxResults": limit,
        "type": "video",
        "key": keys.YOUTUBE_API_KEY,
        "safeSearch": "none",
        "relevanceLanguage": "en",  # Добавляем предпочтение английскому языку
    }
    
    try:
        resp = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("items", []):
            vid = item["id"]["videoId"]
            sn = item["snippet"]
            results.append({
                "video_id": vid,
                "title": sn.get("title"),
                "channel": sn.get("channelTitle"),
                "published_at": sn.get("publishedAt"),
                "thumbnail": (sn.get("thumbnails", {}).get("medium") or sn.get("thumbnails", {}).get("default") or {}).get("url"),
                "url": f"https://www.youtube.com/watch?v={vid}",
            })
        return results
    except Exception as e:
        print(f"Ошибка поиска YouTube для запроса '{query}': {e}")
        return []
