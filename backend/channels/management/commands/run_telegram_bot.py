from django.core.management.base import BaseCommand
from channels.telegram.runner import run_telegram_polling


class Command(BaseCommand):
    help = "Run Telegram bot using long polling for hackathon laptop demonstrations."

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=1,
            help="Polling sleep interval in seconds"
        )

    def handle(self, *args, **options):
        interval = options['interval']
        self.stdout.write(self.style.SUCCESS("Initializing Telegram Bot Polling..."))
        run_telegram_polling(poll_interval=interval)
