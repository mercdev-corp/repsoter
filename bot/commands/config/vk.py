import re
from urllib.parse import urlparse, parse_qs

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler
)

from bot.settings import settings
from bot.vk.client import Client, VK_AUTH_REDIRECT

from bot.commands._states import (
    APP_ID,
    AUTH_URL,
    CANCEL,
    END,
    START,
    VK_CONNECTION,
)
from bot.commands._utils import require_owner
from bot.utils import get_log

from .common import cancel


log = get_log(__name__)


@require_owner
def start(update: Update, context: CallbackContext):
    log.debug('Start VK setup')

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Skip', callback_data=str(APP_ID))]])

    update.callback_query.edit_message_text(
        'Let\'s configure VK connection.\n\n'
        'Send me VK application ID which will be used '
        f'to send API requests to VK (current: `{settings.VK_APP_ID}`).\n\n'
        'You can find your app here: [https://vk.com/apps?act=manage] '
        'on app\'s settings page. If have not one yet, just '
        'create new standalone application and save it. '
        'It\'s not required to publish it.',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    return APP_ID


def _auth_url_text() -> str:
    return (f'Now follow [this URL]({Client().auth_url}) '
            'and confirm access.\n\n'
            'Because we can\'t redirect you from browser to Telegram bot'
            'then you need to send me an URL from browser address field ' 
            f'(current token: `{settings.VK_APP_TOKEN}`).')


@require_owner
def app_id(update: Update, context: CallbackContext):
    log.debug("App ID: %s", update.message.text)
    data = update.message.text.strip()

    if data:
        settings.VK_APP_ID = data

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Skip', callback_data=str(AUTH_URL))]])

    update.message.reply_markdown(
        f'Ok. App ID set to `{settings.VK_APP_ID}`.\n\n'
        f'{_auth_url_text()}',
        reply_markup=keyboard,
    )

    return AUTH_URL


@require_owner
def skip_app_id(update: Update, context: CallbackContext):
    log.info("User did not send a app id.")

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Skip', callback_data=str(AUTH_URL))]])

    update.callback_query.edit_message_text(
        f'Ok, app ID left as: `{settings.VK_APP_ID}`\n\n'
        f'{_auth_url_text()}',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )

    return AUTH_URL


def _done_text() -> str:
    return ('Current VK configuration:\n\n'
            f'`APP ID: {settings.VK_APP_ID}`\n'
            f'`Access Token: {settings.VK_APP_TOKEN}`\n\n'
            'If reposting stops working send /config again.')


@require_owner
def auth_url(update: Update, context: CallbackContext):
    log.debug("Auth URL: %s", update.message.text)
    data = update.message.text.strip()

    if data:
        url = urlparse(data)
        query = parse_qs(url.fragment)
        settings.VK_APP_TOKEN = query.get('access_token', '')[0]

    buttons = [
        [InlineKeyboardButton(text='Configure other', callback_data=str(START))],
    ]

    update.message.reply_markdown(
        _done_text(),
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    return END


@require_owner
def skip_auth_url(update: Update, context: CallbackContext):
    log.debug("User skipped auth URL")
    buttons = [
        [InlineKeyboardButton(text='Configure other', callback_data=str(START))],
    ]

    update.callback_query.edit_message_text(
        _done_text(),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    return END


token_url_regex = re.compile(f'^{re.escape(VK_AUTH_REDIRECT)}.*$', re.I)
id_regex = re.compile(r'^-?\d+$')

handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start, pattern='^' + str(VK_CONNECTION) + '$')],
    states={
        APP_ID: [MessageHandler(Filters.regex(id_regex), app_id),
                 CallbackQueryHandler(skip_app_id, pattern='^' + str(APP_ID) + '$')],
        AUTH_URL: [MessageHandler(Filters.regex(token_url_regex), auth_url),
                   CallbackQueryHandler(skip_auth_url, pattern='^' + str(AUTH_URL) + '$')],
    },
    fallbacks=[CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$')],
    map_to_parent={
        END: START,
    },
    per_message=True,
)
