import logging

from telegram import Chat, ParseMode
from urllib.parse import urlparse


def get_log(name: str) -> logging.Logger:
    return logging.getLogger(name)


log = get_log(__name__)


def parse_proxy_url(url: str):
    res = urlparse(url)
    kwargs = None

    if res.scheme in ['socks5', 'socks5h']:
        if res.username or res.password:
            kwargs = {
                'username': res.username or '',
                'password': res.password or '',
            }

            res.username = None
            res.password = None

            url = urlparse(res)

    return url, kwargs


def get_channel_title(chat: Chat) -> str:
    if chat.title:
        title = chat.title
    elif chat.first_name or chat.last_name:
        title = ' '.join([chat.first_name, chat.last_name]).strip()
    elif chat.username:
        title = f'@{chat.username}'
    else:
        title = 'Private channel'


    log.debug('Chat title fro `%s` is `%s`', chat.id, title)

    return title


def log_message(message: str, level: str = None):
    from .settings import settings

    if not message or not settings.OWNER:
        return

    _level = settings.LOG

    if not _level or (level != _level and _level == 'error'):
        return

    from bot.bot import bot

    bot.send_message(chat_id=settings.OWNER, text=message)
