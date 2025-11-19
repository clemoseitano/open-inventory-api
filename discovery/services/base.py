import uuid
from datetime import timedelta

import django
from oauth2_provider.models import Application, AccessToken, RefreshToken
from oauthlib.oauth2.rfc6749.tokens import random_token_generator


def generate_access_token(user):
    expire_seconds = 36000
    scopes = "read write"

    from django.conf import settings

    application = Application.objects.get(name=settings.APPLICATION_NAME)
    expires = django.utils.timezone.now() + timedelta(seconds=expire_seconds)
    access_token = AccessToken.objects.create(
        user=user,
        application=application,
        token=random_token_generator(None),
        expires=expires,
        scope=scopes,
    )

    refresh_token = RefreshToken.objects.create(
        user=user,
        token=random_token_generator(None),
        access_token=access_token,
        application=application,
    )
    token = {
        "access_token": access_token.token,
        "token_type": "Bearer",
        "expires_in": expire_seconds,
        "refresh_token": refresh_token.token,
        "scope": scopes,
    }
    return token


def schedule_email(args, email_id):
    from django_celery_beat.models import IntervalSchedule, PeriodicTask
    import json

    # Set a task for celery to execute in the background
    schedule, created = IntervalSchedule.objects.get_or_create(
        every=15,
        period=IntervalSchedule.SECONDS,
    )

    PeriodicTask.objects.create(
        interval=schedule,
        name=email_id,
        task="discovery.tasks.send_mails",
        args=json.dumps(args),
    )
