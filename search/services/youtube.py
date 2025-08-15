from typing import Dict, Any, List
import requests
from djspyt import keys

def search_youtube(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    params = {
        "part": "snippet",
        "q": query,
        "maxResults": limit,
        "type": "video",
        "key": keys.YOUTUBE_API_KEY,
        "safeSearch": "none",
    }
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
