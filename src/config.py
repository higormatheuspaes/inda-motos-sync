import os
from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig")

# Firebird
FB_HOST = os.getenv("FB_HOST")
FB_PORT = int(os.getenv("FB_PORT") or 3050)
FB_DATABASE = os.getenv("FB_DATABASE")
FB_USER = os.getenv("FB_USER")
FB_PASSWORD = os.getenv("FB_PASSWORD")
FB_CHARSET = os.getenv("FB_CHARSET") or "UTF8"
FB_CLIENT_LIBRARY = os.getenv("FB_CLIENT_LIBRARY") or None

# Magazord API
MAGAZORD_BASE_URL = os.getenv("MAGAZORD_BASE_URL")
MAGAZORD_TOKEN = os.getenv("MAGAZORD_TOKEN")
MAGAZORD_SENHA = os.getenv("MAGAZORD_SENHA")

# E-mail (notificação de erros)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT") or 587)
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO")