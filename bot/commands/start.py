from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, CommandHandler, ConversationHandler, Filters, MessageHandler

from bot.settings import settings
from bot.utils import get_log

from ._utils import require_user


log = get_log(__name__)
PASSWORD = 0


@require_user
def start(update: Update, context: CallbackContext):
    log.debug('Taken command `start`')
    user = update.effective_user

    if settings.OWNER:
        if user.id == settings.OWNER:
            update.message.reply_markdown(
                'Greetings, my master!',
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        else:
            update.message.reply_markdown(
                'You are not my master!',
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

    update.message.reply_markdown(
        'Hi! Bot not configured. Say password '
        'so i can be sure you are my master.',
        reply_markup=ReplyKeyboardRemove()
    )
    log.debug('Password next step `%s`', PASSWORD)
    return PASSWORD


@require_user
def password(update: Update, context: CallbackContext):
    log.debug('Process password')
    user = update.effective_user

    if settings.OWNER:
        if user.id == settings.OWNER:
            update.message.reply_markdown(
                'Greetings, my master!',
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        else:
            update.message.reply_markdown(
                'You are not my master!',
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

    text = update.effective_message.text.strip()

    if text == settings.PASSWORD:
        settings.OWNER = user.id
        text = 'Greetings, my master! I\'m at your service!'

        if not settings.VK_APP_ID or not settings.VK_APP_TOKEN:
            text += '\n\nSend /config to configure me.'

        update.message.reply_markdown(
            text,
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_markdown(
            'Nope! Think better!',
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    user = update.effective_user
    log.debug("User %s canceled the conversation.", user.first_name)
    update.message.reply_markdown('As you wish 🤷🏻‍♂️',
                                  reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],

    states={
        PASSWORD: [MessageHandler(Filters.update.message, password)],
    },

    fallbacks=[CommandHandler('cancel', cancel)]
)
