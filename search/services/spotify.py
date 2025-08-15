import base64
import time
from typing import Dict, Any, List
import requests
from djspyt import keys

_token_cache = {"access_token": None, "expires_at": 0}

def _get_access_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    auth_str = f"{keys.SPOTIFY_CLIENT_ID}:{keys.SPOTIFY_CLIENT_SECRET}".encode("utf-8")
    b64 = base64.b64encode(auth_str).decode("utf-8")

    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {b64}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token_cache["access_token"]

def search_tracks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    token = _get_access_token()
    params = {"q": query, "type": "track", "limit": limit}
    resp = requests.get(
        "https://api.spotify.com/v1/search",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    items = payload.get("tracks", {}).get("items", [])
    results = []
    for it in items:
        results.append({
            "id": it["id"],
            "name": it["name"],
            "artists": ", ".join(a["name"] for a in it.get("artists", [])),
            "album": it.get("album", {}).get("name"),
            "image": (it.get("album", {}).get("images") or [{}])[0].get("url"),
            "duration_ms": it.get("duration_ms"),
            "preview_url": it.get("preview_url"),
            "external_url": it.get("external_urls", {}).get("spotify"),
        })
    return results

def get_track_metadata(track_id: str) -> Dict[str, Any]:
    token = _get_access_token()
    resp = requests.get(
        f"https://api.spotify.com/v1/tracks/{track_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    resp.raise_for_status()
    t = resp.json()
    meta = {
        "id": t["id"],
        "name": t["name"],
        "artists": ", ".join(a["name"] for a in t.get("artists", [])),
        "album": t.get("album", {}).get("name"),
        "release_date": t.get("album", {}).get("release_date"),
        "image": (t.get("album", {}).get("images") or [{}])[0].get("url"),
        "duration_ms": t.get("duration_ms"),
        "popularity": t.get("popularity"),
        "track_number": t.get("track_number"),
        "disc_number": t.get("disc_number"),
        "explicit": t.get("explicit"),
        "preview_url": t.get("preview_url"),
        "external_url": t.get("external_urls", {}).get("spotify"),
    }
    return meta
