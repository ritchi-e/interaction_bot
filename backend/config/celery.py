import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("caller")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "dispatch-due-calls": {
        "task": "apps.calls.tasks.dispatch_due_calls",
        "schedule": 60.0,
    }
}
