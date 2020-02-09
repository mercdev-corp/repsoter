from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    TelegramError,
    Update
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
)

from bot.bot import bot
from bot.settings import settings

from bot.commands._states import (
    ADD_MAP,
    CANCEL,
    DEL_MAP,
    OPTION,
    START,
    VK_CONNECTION,
)
from bot.commands._utils import require_owner
from bot.utils import get_log, get_channel_title
from bot.vk.client import Client

from .add_map import handler as add_map_conv
from .common import cancel
from .del_map import handler as del_map_conv
from .vk import handler as vk_con_conv


log = get_log(__name__)


def build_info() -> str:
    text = ''
    chats = {}
    groups = {}
    repost_map = settings.REPOST_MAP or {}
    number = 0

    for chat_id in repost_map.get('TG', {}):

        if chat_id not in chats:
            try:
                chat = bot.get_chat(chat_id)
                chats[chat_id] = chat
            except TelegramError:
                chats[chat_id] = None

        chat = chats[chat_id]

        for group_id in repost_map['TG'][chat_id].get('targets', []):
            number += 1

            if group_id not in groups:
                group = Client().groups_get_by_id(group_id=group_id)

                if not group:
                    groups[group_id] = None
                else:
                    groups[group_id] = group[0]

            group = groups[group_id]

            text += f"{number}. \"{get_channel_title(chat)}\" 👉 \"{group['name']}\"\n"

    return text


@require_owner
def start(update: Update, context: CallbackContext):
    log.debug('Taken command `config`')

    if settings.VK_APP_ID and settings.VK_APP_TOKEN:
        info = build_info()

        if info:
            text = f'Currently configured:\n```\n{info}```\nWhat you want more to configure?'
        else:
            text = 'What you want to configure?'

        buttons = [
            [InlineKeyboardButton(text='Add TG to VK relation', callback_data=str(ADD_MAP))],
        ]

        if (settings.REPOST_MAP or {}).get('TG', {}):
            buttons.append([InlineKeyboardButton(text='Remove TG to VK relation', callback_data=str(DEL_MAP))])
    else:
        text = 'For first you need to setup VK connection.'
        buttons = []

    buttons += [
        [InlineKeyboardButton(text='Configure VK connection', callback_data=str(VK_CONNECTION))],
        [InlineKeyboardButton(text='Cancel', callback_data=str(CANCEL))]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    if update.message:
        update.message.reply_markdown(
            text=text,
            reply_markup=keyboard,
        )
    else:
        update.callback_query.edit_message_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

    return OPTION


handler = ConversationHandler(
    entry_points=[CommandHandler('config', start)],

    states={
        START: [CallbackQueryHandler(start, pattern='^' + str(START) + '$')],
        OPTION: [
            add_map_conv,
            del_map_conv,
            vk_con_conv,
            CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$'),
        ],
        CANCEL: [CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$')],
    },

    fallbacks=[CommandHandler('cancel', cancel)],
)
