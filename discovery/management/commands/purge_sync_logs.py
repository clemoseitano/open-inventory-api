from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from discovery.models import SyncPushLog, SyncJournal


class Command(BaseCommand):
    help = "Purges old sync logs and journal entries to maintain performance."

    def handle(self, *args, **options):
        # TODO: Before purge, write all records to a log file. We won't read it ever but in case the user requests, we should have it
        # 1. Purge raw push logs (Keep 1 day)
        push_cutoff = timezone.now() - timedelta(days=1)
        deleted_push, _ = SyncPushLog.objects.filter(
            created_at__lt=push_cutoff
        ).delete()

        # 2. Purge journal entries (Keep 30 days)
        # Note: This triggers the 'FULL_SYNC_REQUIRED' for clients older than 30 days.
        journal_cutoff = timezone.now() - timedelta(days=30)
        deleted_journal, _ = SyncJournal.objects.filter(
            created_at__lt=journal_cutoff
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Purged {deleted_push} push logs and {deleted_journal} journal entries."
            )
        )
