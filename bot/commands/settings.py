from telegram import Update
from telegram.ext import CallbackContext, CommandHandler

from bot.settings import settings
from bot.utils import get_log

from ._utils import require_owner


log = get_log(__name__)


@require_owner
def command(update: Update, context: CallbackContext):
    log.debug('Taken command `settings`')
    update.message.reply_markdown('Current VK configuration:\n\n'
                                  f'`APP ID: {settings.VK_APP_ID}`\n'
                                  f'`Group ID: {settings.VK_WALL_ID}`\n'
                                  f'`Access Token: {settings.VK_APP_TOKEN}`\n\n'
                                  'Call /config to update it.')


handler = CommandHandler('settings', command)
