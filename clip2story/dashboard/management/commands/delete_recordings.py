from django.core.management.base import BaseCommand, CommandError
from dashboard.models import Recording


class Command(BaseCommand):
    help = "Deletes recordings older than a specified time."

    def handle(self, *args, **options):
        Recording.remove_old_recordings()

        self.stdout.write(
            self.style.SUCCESS('Successfully deleted old recordings.')
        )