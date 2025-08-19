from typing import Dict, Any, List
import requests
import re
from .youtube_key_manager import key_manager

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
    """Выполняет один поисковый запрос к YouTube API с автоматической ротацией ключей"""
    
    # Пробуем все доступные ключи
    for attempt in range(key_manager.get_available_keys_count() + 1):
        current_key = key_manager.get_current_key()
        if not current_key:
            print("❌ Нет доступных ключей YouTube API")
            return []
        
        params = {
            "part": "snippet",
            "q": query,
            "maxResults": limit,
            "type": "video",
            "key": current_key,
            "safeSearch": "none",
            "relevanceLanguage": "en",
        }

        try:
            resp = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=15)
            
            # Проверяем статус ответа
            if resp.status_code == 200:
                data = resp.json()
                
                # Проверяем наличие ошибок в ответе
                if "error" in data:
                    error = data["error"]
                    error_code = error.get('code')
                    error_message = error.get('message', '')
                    
                    # Если ошибка связана с ключом API, помечаем его как неработающий
                    if error_code in [403, 400] or "quota" in error_message.lower() or "key" in error_message.lower():
                        key_manager.mark_key_failed(current_key, f"Код {error_code}: {error_message}")
                        continue  # Пробуем следующий ключ
                    else:
                        print(f"❌ YouTube API вернул ошибку для запроса '{query}':")
                        print(f"   Код: {error_code}")
                        print(f"   Сообщение: {error_message}")
                        return []
                
                # Успешный ответ
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
                
            elif resp.status_code == 403:
                # Ключ заблокирован или превышена квота
                error_text = resp.text[:200]
                key_manager.mark_key_failed(current_key, f"403 Forbidden: {error_text}")
                continue  # Пробуем следующий ключ
                
            elif resp.status_code == 400:
                # Неверный запрос
                error_text = resp.text[:200]
                key_manager.mark_key_failed(current_key, f"400 Bad Request: {error_text}")
                continue  # Пробуем следующий ключ
                
            else:
                print(f"❌ Неожиданный статус YouTube API для запроса '{query}': {resp.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка сети при поиске YouTube для запроса '{query}': {e}")
            return []
        except Exception as e:
            print(f"❌ Неожиданная ошибка при поиске YouTube для запроса '{query}': {e}")
            return []
    
    # Если все ключи исчерпаны
    print(f"❌ Все ключи YouTube API исчерпаны для запроса '{query}'")
    raise Exception("Упс, похоже закончились ключи. Сообщите об ошибке в Telegram: @Vie333")
