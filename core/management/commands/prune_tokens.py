from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import JWTGrant


class Command(BaseCommand):
    help = "Delete expired access token fingerprints (schedule daily)."

    def handle(self, *args, **options):
        count, _ = JWTGrant.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f"Deleted {count} expired grants")
