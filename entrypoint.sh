#!/bin/sh
set -e

python manage.py migrate --noinput

if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")

if email and password:
    user = User.objects.filter(email=email).first()
    if not user:
        User.objects.create_superuser(email=email, username=username, password=password)
    else:
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if hasattr(user, "is_verified"):
            user.is_verified = True
        if not getattr(user, "username", ""):
            user.username = username
        user.set_password(password)
        user.save()
PY
fi

python manage.py collectstatic --noinput

WORKERS=${UVICORN_WORKERS:-}
if [ -z "$WORKERS" ]; then
  if [ "$USE_REDIS_CHANNELS" = "true" ] || [ "$USE_REDIS_CHANNELS" = "1" ]; then
    WORKERS=3
  else
    WORKERS=1
  fi
fi

exec uvicorn core.asgi:application --host 0.0.0.0 --port 8000 --workers ${WORKERS}
