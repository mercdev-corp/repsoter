from telegram import Bot

from .settings import settings


bot = Bot(token=settings.TG_BOT_TOKEN)
