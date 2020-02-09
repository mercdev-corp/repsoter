from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from bot.commands._states import END
from bot.commands._utils import require_owner
from bot.utils import get_log


log = get_log(__name__)


@require_owner
def cancel(update: Update, context: CallbackContext):
    log.debug("User canceled the conversation.")
    text = 'Configuration done. Send /config to start again.'

    if update.message:
        update.message.reply_markdown(
            text
        )
    else:
        update.callback_query.edit_message_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )

    return END
