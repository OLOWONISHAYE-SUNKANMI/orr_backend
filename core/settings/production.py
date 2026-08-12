import os
from .base import *
from urllib.parse import urlparse, parse_qs, unquote
from decouple import config

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = ["*"] # Cloud Run handles host validation, but we can be specific if needed

DATABASE_URL = config("DATABASE_URL")
DB_PASSWORD = config("DB_PASSWORD", default=None)

if DATABASE_URL:
    url = urlparse(DATABASE_URL)
    query_params = parse_qs(url.query)
    
    db_host = query_params.get('host', [url.hostname])[0]
    
    if db_host and db_host.startswith('/'):
        db_host = unquote(db_host)

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": url.path[1:],
            "USER": url.username,
            "PASSWORD": DB_PASSWORD or (unquote(url.password) if url.password else None),
            "HOST": db_host,            
            "PORT": url.port or "5432",
        }
    }
else:
    raise ValueError("DATABASE_URL is not set")

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'ALLOWALL'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# CORS settings for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://admin.orr.solutions",
    "https://orr.solutions",
    "https://www.orr.solutions",
    "https://consultant.orr.solutions",
    "https://projectmanager.orr.solutions",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
    "http://localhost:3003",
    "http://127.0.0.1:3003",
    "http://localhost:3004",
    "http://127.0.0.1:3004",
    "http://localhost:3005",
    "http://127.0.0.1:3005",
    "http://localhost:3006",
    "http://127.0.0.1:3006",
    "https://orr-backend-105825824472.asia-southeast2.run.app",
]

CORS_ALLOW_CREDENTIALS = True

# CSRF settings
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
    "http://localhost:3003",
    "http://127.0.0.1:3003",
    "http://localhost:3004",
    "http://127.0.0.1:3004",
    "http://localhost:3005",
    "http://127.0.0.1:3005",
    "http://localhost:3006",
    "http://127.0.0.1:3006",
    "https://orr-backend-105825824472.asia-southeast2.run.app",
    "https://orr.solutions",
    "https://www.orr.solutions",
    "https://orr-solutions.vercel.app",
    "https://orr-admin-frontend.vercel.app",
    "https://orr-solutions-admin.vercel.app",
    "https://admin.orr.solutions",
    "https://consultant.orr.solutions",
    "https://projectmanager.orr.solutions",
]

# Storage settings for Django 4.2+
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

GS_BUCKET_NAME = config('GS_BUCKET_NAME', default='orr-solutions-media')
GS_PROJECT_ID = config('GS_PROJECT_ID', default='orr-core-platform')
GS_DEFAULT_ACL = 'publicRead'
GS_QUERYSTRING_AUTH = False
GS_FILE_OVERWRITE = False
GS_EXPIRATION = None # Ensure URLs don't expire
GS_OBJECT_PARAMETERS = {
    'content_disposition': 'inline',
    'cache_control': 'public, max-age=3600',
}
GS_BLOB_CHUNK_SIZE = 1024 * 1024 * 5  # 5MB chunks for better streaming

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name} — {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": "INFO",
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "INFO", "propagate": True},
    },
}



