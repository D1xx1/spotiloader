import re
import urllib.parse
import json
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, Http404, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import SearchForm
from .services.spotify import search_tracks, get_track_metadata
from .services.youtube import search_youtube
from .services.ytdl import download_mp3
from .services.youtube_key_manager import key_manager

# Глобальный словарь для хранения прогресса
download_progress = {}

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
    yt_error = None
    try:
        yt_results = search_youtube(yt_query, limit=6)
    except Exception as e:
        yt_error = str(e)
        yt_results = []
        # Если это сообщение о закончившихся ключах, не показываем другие ошибки
        if "закончились ключи" in str(e):
            yt_error = str(e)
    context = {
        "meta": meta, 
        "yt_query": yt_query, 
        "yt_results": yt_results, 
        "yt_error": yt_error
    }
    return render(request, "search/track_detail.html", context)

def youtube_audio(request: HttpRequest, video_id: str) -> HttpResponse:
    """Download YouTube audio and return it as an MP3 file."""
    try:
        # Инициализируем прогресс
        download_progress[video_id] = {
            'status': 'starting',
            'progress': 0,
            'message': 'Начинаем загрузку...'
        }
        
        # Создаем кастомный callback для отслеживания прогресса
        def progress_callback(d):
            if d['status'] == 'downloading':
                # Вычисляем процент прогресса
                if 'total_bytes' in d and d['total_bytes']:
                    progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                    progress = int((d['downloaded_bytes'] / d['total_bytes_estimate']) * 100)
                else:
                    progress = 0
                
                download_progress[video_id] = {
                    'status': 'downloading',
                    'progress': progress,
                    'message': f'Загружено {d.get("downloaded_bytes", 0)} байт'
                }
            elif d['status'] == 'finished':
                download_progress[video_id] = {
                    'status': 'processing',
                    'progress': 95,
                    'message': 'Обрабатываем аудио...'
                }
                
                # Добавляем промежуточные обновления во время обработки
                import threading
                import time
                
                def update_processing_progress():
                    for i in range(96, 100):
                        time.sleep(0.5)  # Обновляем каждые 500мс
                        if video_id in download_progress and download_progress[video_id]['status'] == 'processing':
                            download_progress[video_id] = {
                                'status': 'processing',
                                'progress': i,
                                'message': 'Обрабатываем аудио...'
                            }
                
                # Запускаем обновления в отдельном потоке
                threading.Thread(target=update_processing_progress, daemon=True).start()
        
        # Скачиваем с отслеживанием прогресса
        data, filename = download_mp3(video_id, progress_callback)
        
        # Обновляем прогресс на завершение
        download_progress[video_id] = {
            'status': 'completed',
            'progress': 100,
            'message': 'Загрузка завершена'
        }
        
    except Exception as e:
        # Обновляем прогресс на ошибку
        download_progress[video_id] = {
            'status': 'error',
            'progress': 0,
            'message': f'Ошибка: {str(e)}'
        }
        return HttpResponse(f"Не удалось получить аудио: {e}", status=502)

    # Очищаем имя файла от недопустимых символов
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_filename = safe_filename.replace('\n', ' ').replace('\r', ' ').strip()
    safe_filename = re.sub(r'\s+', ' ', safe_filename)

    # Кодируем имя файла для HTTP заголовка
    encoded_filename = urllib.parse.quote(safe_filename)

    # Улучшенные заголовки для гарантированного скачивания
    resp = HttpResponse(data, content_type="audio/mpeg")
    resp["Content-Disposition"] = f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{encoded_filename}'
    resp["Content-Length"] = str(len(data))
    resp["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp["Pragma"] = "no-cache"
    resp["Expires"] = "0"
    resp["X-Content-Type-Options"] = "nosniff"
    return resp

@csrf_exempt
def progress_stream(request, video_id):
    """Stream progress updates for download"""
    def event_stream():
        while True:
            if video_id in download_progress:
                progress = download_progress[video_id]
                yield f"data: {json.dumps(progress)}\n\n"
                
                # Закрываем соединение только при полном завершении или ошибке
                if progress.get('status') in ['completed', 'error']:
                    # Удаляем прогресс после завершения
                    if video_id in download_progress:
                        del download_progress[video_id]
                    break
            
            import time
            time.sleep(0.1)  # Проверяем каждые 100мс
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
