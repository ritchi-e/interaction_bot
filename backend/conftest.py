import os

os.environ.setdefault("USE_SQLITE", "1")
os.environ.setdefault("CELERY_EAGER", "1")
os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret")
os.environ.setdefault("FERNET_KEY", "24fVl3QzAELBCLymBOb7R4r1uSDISkGYzIj7cIYi5po=")
os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal")
os.environ.setdefault("DOGRAH_WEBHOOK_SECRET", "test-dograh-secret")
os.environ.setdefault("DOGRAH_API_URL", "http://dograh.test")
os.environ.setdefault("DOGRAH_API_KEY", "test-dograh-key")
