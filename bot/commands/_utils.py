from telegram.ext import ConversationHandler

from bot.utils import log_message
from bot.settings import settings
from bot.utils import get_log


log = get_log(__name__)


def check_source(func):
    def wrapped(update, context=None):
        chat = update.effective_chat
        allowed = settings.REPOST_MAP or {}
        chats = [int(val) for val in allowed.get('TG', {}).keys()]

        if not chat or chat.id not in chats:
            log.debug('Avoid to run wrong source handler `%s.%s`', func.__module__, func.__name__)
            return ConversationHandler.END

        return func(update, context)

    return wrapped


def require_user(func):
    def wrapped(update, context=None):
        user = update.effective_user

        if not user:
            log.debug('Avoid to run wrong user handler `%s.%s`', func.__module__, func.__name__)
            return ConversationHandler.END

        return func(update, context)

    return wrapped


def require_owner(func):
    def wrapped(update, context=None):
        user = update.effective_user

        if not user or user.id != settings.OWNER:
            log.debug('Avoid to run wrong owner handler `%s.%s`', func.__module__, func.__name__)
            return ConversationHandler.END

        return func(update, context)

    return wrapped
