# Django: Spotify → YouTube Finder (smart)

Поддерживает:
- Поиск по названию
- Вставку ссылки/URI/ID трека Spotify прямо в поиск (умный редирект на детальную страницу)

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Добавьте ключи в `djspyt/keys.py`:
```python
SPOTIFY_CLIENT_ID = "ваш_id"
SPOTIFY_CLIENT_SECRET = "ваш_secret"
YOUTUBE_API_KEY = "ваш_api_key"
```

Запустите:
```bash
python manage.py migrate
python manage.py runserver 8080
```

### Форматы, которые понимает поиск
- Название: `Linkin Park - Numb`
- URL: `https://open.spotify.com/track/6habFhsOp2NvshLv26DqMb?si=...`
- URI: `spotify:track:6habFhsOp2NvshLv26DqMb`
- Сам ID (22 символа): `6habFhsOp2NvshLv26DqMb`
