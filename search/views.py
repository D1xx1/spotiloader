import re
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, Http404, StreamingHttpResponse
from .forms import SearchForm
from .services.spotify import search_tracks, get_track_metadata
from .services.youtube import search_youtube
from .services.ytdl import get_direct_audio

_SPOTIFY_URL_RE = re.compile(
    r"""
    ^https?://
    (?:open|play|music)\.spotify\.com/
    (?:intl-[a-z]{2}/)?
    track/
    (?P<id>[A-Za-z0-9]{22})
    (?:[^\s]*)?$
    """, re.IGNORECASE | re.VERBOSE
)
_SPOTIFY_URI_RE = re.compile(r"^spotify:track:(?P<id>[A-Za-z0-9]{22})$", re.IGNORECASE)

def extract_spotify_track_id(text: str):
    if not text:
        return None
    text = text.strip()
    m = _SPOTIFY_URL_RE.match(text)
    if m:
        return m.group("id")
    m = _SPOTIFY_URI_RE.match(text)
    if m:
        return m.group("id")
    # Иногда делятся просто 22-символьным ID
    if re.fullmatch(r"[A-Za-z0-9]{22}", text):
        return text
    return None

def ms_to_mmss(ms) -> str:
    try:
        ms = int(ms)
    except (TypeError, ValueError):
        return "—"
    s = ms // 1000
    m, ss = divmod(s, 60)
    return f"{m}:{ss:02d}"

def search_view(request: HttpRequest) -> HttpResponse:
    form = SearchForm(request.GET or None)
    results = []
    query = None
    error = None
    if form.is_valid():
        query = form.cleaned_data["q"]
        # 1) Если вставили ссылку/URI/ID трека — сразу на детальную
        track_id = extract_spotify_track_id(query)
        if track_id:
            return redirect("track_detail", track_id=track_id)
        # 2) Иначе — обычный текстовый поиск
        try:
            results = search_tracks(query, limit=12)
            for t in results:
                t["duration_str"] = ms_to_mmss(t.get("duration_ms"))
        except Exception as e:
            error = str(e)
    context = {"form": form, "results": results, "query": query, "error": error}
    return render(request, "search/search.html", context)

def track_detail(request: HttpRequest, track_id: str) -> HttpResponse:
    try:
        meta = get_track_metadata(track_id)
    except Exception as e:
        raise Http404(f"Spotify трек не найден или недоступен: {e}")

    meta["duration_str"] = ms_to_mmss(meta.get("duration_ms"))
    yt_query = f"{meta['artists']} - {meta['name']}"
    yt_results = []
    try:
        yt_results = search_youtube(yt_query, limit=6)
    except Exception:
        yt_results = []
    context = {"meta": meta, "yt_query": yt_query, "yt_results": yt_results}
    return render(request, "search/track_detail.html", context)



def youtube_audio(request: HttpRequest, video_id: str):
    """
    Stream the best available YouTube audio to the user as an attachment.
    Uses yt-dlp to resolve a direct CDN URL and proxies the stream.
    """
    try:
        stream_url, filename, mime = get_direct_audio(video_id)
    except Exception as e:
        return HttpResponse(f"Не удалось получить аудио: {e}", status=502)

    import requests
    try:
        upstream = requests.get(stream_url, stream=True, timeout=30)
        upstream.raise_for_status()
    except Exception as e:
        return HttpResponse(f"Ошибка при обращении к CDN: {e}", status=502)

    resp = StreamingHttpResponse(upstream.iter_content(chunk_size=8192), content_type=mime or "application/octet-stream")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    # Forward a couple of useful headers if present
    if "Content-Length" in upstream.headers:
        resp["Content-Length"] = upstream.headers["Content-Length"]
    return resp
