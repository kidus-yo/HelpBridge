"""
Long Polling Runner for Telegram Bot.
Fulfills the Hackathon Technical Guide instruction:
'create a bot with BotFather and read messages with getUpdates long polling.
 No public server address is needed, so it runs from a laptop.'
"""

import time
import logging
from channels.telegram.client import TelegramClient
from channels.telegram.bot import TelegramBotHandler

logger = logging.getLogger(__name__)


def run_telegram_polling(poll_interval: int = 1):
    """Starts continuous long polling loop."""
    client = TelegramClient()
    if not client.is_configured:
        print("⚠️ TELEGRAM_BOT_TOKEN is not set in environment or settings.")
        print("Set TELEGRAM_BOT_TOKEN in .env to run live Telegram polling.")
        return

    handler = TelegramBotHandler(client=client)
    print("🚀 Starting Telegram Bot Long-Polling runner...")
    print("Press Ctrl+C to stop.")

    offset = None
    while True:
        try:
            updates = client.get_updates(offset=offset, timeout=20)
            for upd in updates:
                upd_id = upd.get("update_id")
                if upd_id is not None:
                    offset = upd_id + 1
                handler.handle_update(upd)
        except KeyboardInterrupt:
            print("\n🛑 Telegram polling stopped.")
            break
        except Exception as err:
            logger.error("Error in Telegram polling loop: %s", err)
            time.sleep(3)
        time.sleep(poll_interval)
