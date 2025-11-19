import json
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from oauth2_provider.models import Application

from discovery.models import AdminConfiguration


class Command(BaseCommand):
    help = "Create OAuth application and configs."

    def handle(self, *args, **options):
        # Create superuser
        username = os.environ.get("ADMIN_EMAIL")
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created superuser {email}")
            )
        else:
            self.stdout.write(f"Superuser {email} already exists.")

        # Create OAuth application
        try:
            app, created = Application.objects.get_or_create(
                name=os.environ.get("APPLICATION_NAME"),
                user=User.objects.get(username=username),
                client_type=Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_PASSWORD,
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully created OAuth application {app.name}"
                    )
                )
            else:
                self.stdout.write("OAuth application already exists.")
        except ObjectDoesNotExist:
            self.stdout.write(self.style.ERROR(f"Superuser {username} does not exist."))

        values = json.loads(open("discovery/management/commands/data.json").read())
        environment_name = os.environ.get("ENV", None)
        environment_name = (
            "local" if not environment_name else environment_name
        ).lower()
        configs = values.get(environment_name)
        # Update default site
        try:
            default_site = Site.objects.get(id=settings.SITE_ID)
            default_site.name = os.environ.get("APPLICATION_NAME")
            default_site.domain = configs.get("DOMAIN")
            default_site.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated site object {default_site.name}"
                )
            )
            for key, val in configs.items():
                instance, is_created = AdminConfiguration.objects.get_or_create(
                    key=key,
                    value=val,
                    type="string",
                )
                if is_created:
                    self.stdout.write(
                        self.style.SUCCESS(f"Successfully created config {key}")
                    )
        except ObjectDoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Site {settings.SITE_ID} does not exist.")
            )
