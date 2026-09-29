import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
FERNET_KEY = os.environ.get("FERNET_KEY", "")
if not SECRET_KEY:
    if DEBUG or os.environ.get("USE_SQLITE") == "1":
        SECRET_KEY = "dev-only-secret"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY is required")
if not FERNET_KEY:
    if DEBUG or os.environ.get("USE_SQLITE") == "1":
        FERNET_KEY = "24fVl3QzAELBCLymBOb7R4r1uSDISkGYzIj7cIYi5po="
    else:
        raise RuntimeError("FERNET_KEY is required")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.tenants",
    "apps.campaigns",
    "apps.agents",
    "apps.compliance",
    "apps.whatsapp",
    "apps.calls",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

AUTH_USER_MODEL = "tenants.User"

if os.environ.get("USE_SQLITE") == "1":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "caller"),
            "USER": os.environ.get("POSTGRES_USER", "caller"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "caller"),
            "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
CORS_ALLOW_HEADERS = ["authorization", "content-type", "x-internal-token"]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_EAGER", "0") == "1"
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TIMEZONE = "Asia/Kolkata"

INTERNAL_API_TOKEN = os.environ.get("INTERNAL_API_TOKEN", "")
DOGRAH_API_URL = os.environ.get("DOGRAH_API_URL", "http://localhost:8000")
DOGRAH_API_KEY = os.environ.get("DOGRAH_API_KEY", "")
DOGRAH_WEBHOOK_SECRET = os.environ.get("DOGRAH_WEBHOOK_SECRET", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")
SIP_HOSTNAME = os.environ.get("SIP_HOSTNAME", "sip.example.com")
ASTERISK_CONFIG_DIR = os.environ.get("ASTERISK_CONFIG_DIR", "")
ASTERISK_AMI_HOST = os.environ.get("ASTERISK_AMI_HOST", "")
ASTERISK_AMI_PORT = int(os.environ.get("ASTERISK_AMI_PORT", "5038"))
ASTERISK_AMI_USER = os.environ.get("ASTERISK_AMI_USER", "caller")
ASTERISK_AMI_SECRET = os.environ.get("ASTERISK_AMI_SECRET", "")

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY") or os.environ.get("deepgram_nova3_api", "")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
RUMIK_API_KEY = os.environ.get("RUMIK_API_KEY", "")
RUMIK_API_URL = os.environ.get("RUMIK_API_URL", "")
RUMIK_TTS_MODEL = os.environ.get("RUMIK_TTS_MODEL", "")
RUMIK_TTS_DEFAULT_SPEAKER = os.environ.get("RUMIK_TTS_DEFAULT_SPEAKER", "")

CALLING_WINDOW_START_HOUR = 9
CALLING_WINDOW_END_HOUR = 21
MAX_CALLS_PER_LEAD_CAMPAIGN_HOURS = 24
