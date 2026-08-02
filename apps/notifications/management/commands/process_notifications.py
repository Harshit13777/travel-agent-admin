from django.core.management.base import BaseCommand
from apps.notifications.services.dispatcher_service import DispatcherService

class Command(BaseCommand):
    help = 'Process pending notifications via DispatcherService'

    def handle(self, *args, **options):
        self.stdout.write("Starting notification processing...")
        DispatcherService.process_pending()
        self.stdout.write("Finished notification processing.")
