import re

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
    Filters,
    MessageHandler
)

from bot.bot import bot
from bot.utils import get_channel_title
from bot.settings import settings
from bot.vk.client import Client, VK_AUTH_REDIRECT

from bot.commands._states import (
    ADD_MAP,
    CANCEL,
    END,
    START,
    ADD_CHANNEL_ID,
    ADD_PUBLIC_ID,
)
from bot.commands._utils import require_owner
from bot.utils import get_log

from .common import cancel


log = get_log(__name__)


@require_owner
def start(update: Update, context: CallbackContext):
    log.debug('Start adding map')

    channels = settings.REPOST_MAP
    buttons = []
    configured = ''
    number = 0

    if channels:
        chats = []

        for channel in channels.get('TG', {}):
            chat = bot.get_chat(channel)
            number += 1
            chats.append(InlineKeyboardButton(text=str(number), callback_data=f'add_map__{channel}'))
            configured += f'{number}. {get_channel_title(chat)}\n'

        if chats:
            buttons.append(chats)

    buttons.append([InlineKeyboardButton(text='Cancel', callback_data=str(START))])
    keyboard = InlineKeyboardMarkup(buttons)

    text = (
        'Let\'s configure TG to VK reposting.\n\n'
        'Send me source TG chat\'s @username or '
        'forward any message from it.'
    )

    if configured:
        text += (
            '\nOr select existed one to add reposting to another '
            f'VK group:\n\n{configured}'
        )

    update.callback_query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    return ADD_CHANNEL_ID


@require_owner
def add_channel_id(update: Update, context: CallbackContext):
    log.debug('Adding channel')
    message = update.message
    channel = None
    is_new = True
    text = ''
    buttons = []

    if message:
        if message.forward_from_chat:
            channel = message.forward_from_chat
            chat_id = message.forward_from_chat.id
        else:
            chat_id = (message.text or '').strip()
    else:
        is_new = False
        chat_id = update.callback_query.data.split('__')[-1]

    log.debug('Source chat id `%s`.', chat_id)

    if chat_id and not channel:
        try:
            channel = bot.get_chat(chat_id)
            chat_id = channel.id
        except TelegramError:
            log.debug('Can\'t find channel for `%s`, please try again.', chat_id)
            text = f'Can\'t find channel for `{chat_id}`, please try again.'

            if is_new:
                message.reply_markdown(
                    text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Start again', callback_data=str(ADD_MAP))]])
                )
            else:
                update.callback_query.edit_message_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    keyboard_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Start again', callback_data=str(ADD_MAP))]])
                )
            return ADD_CHANNEL_ID

    vk_groups = Client().groups_get()
    groups = []

    if not vk_groups.get('count', 0):
        text = (
            'Can\'t find any accessible VK group.\n\n'
            'You need to have administrator, editor, '
            'moderator or advertiser access rights to some '
            'group for first to allow me create posts in it…'
        )

        if is_new:
            message.reply_markdown(text)
        else:
            update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                keyboard_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Start again', callback_data=str(ADD_MAP))]])
            )

        return ADD_MAP

    title = get_channel_title(channel)

    if is_new:
        text += (f'Added new source channel `{title}`.\n\n'
                 'Don\'t forget to add me as administrator to '
                 'this channel!')
    else:
        text += f'Selected existed source channel `{title}`.\n'

    text += 'Now select target VK group ' \
            '(groups where you have access to post):\n\n'

    context.user_data['ADDING_CHANNEL'] = chat_id
    number = 0

    for group in vk_groups['items']:
        number += 1
        text += f"{number}. {group['name']}\n"
        groups.append(InlineKeyboardButton(text=f'{number}', callback_data=f"add_group__{group['id']}"))

    if groups:
        buttons.append(groups)

    buttons.append([InlineKeyboardButton(text='Cancel', callback_data=str(START))])
    keyboard = InlineKeyboardMarkup(buttons)

    if is_new:
        message.reply_markdown(
            text,
            reply_markup=keyboard
        )
    else:
        update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

    return ADD_PUBLIC_ID


@require_owner
def add_group_id(update: Update, context: CallbackContext):
    buttons = [
        [InlineKeyboardButton(text='Start again', callback_data=str(ADD_MAP))],
    ]

    if not context.user_data['ADDING_CHANNEL']:
        log.debug('Source channel not defined')

        update.callback_query.edit_message_text(
            'Source channel not defined',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return ADD_MAP

    group_id = update.callback_query.data.split('__')[-1]
    chat_id = context.user_data['ADDING_CHANNEL']

    try:
        chat = bot.get_chat(chat_id)
    except TelegramError:
        log.debug('Source chat not found `%s`', chat_id)

        update.callback_query.edit_message_text(
            'Source chat not found',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        return ADD_MAP

    if not group_id:
        log.debug('Target group id not defined')

        update.callback_query.edit_message_text(
            'Target group id not defined',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        return ADD_MAP

    groups = Client().groups_get_by_id(group_id=group_id)

    if not groups:
        log.debug('Target group id not found `%s`', group_id)

        update.callback_query.edit_message_text(
            'Target group not found.',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        return ADD_MAP

    group = groups[0]
    repost_map = settings.REPOST_MAP or {}

    if 'TG' not in repost_map:
        repost_map['TG'] = {}

    str_chat_id = str(chat_id)

    if str_chat_id not in repost_map['TG']:
        repost_map['TG'][str_chat_id] = {}

    if 'targets' not in repost_map['TG'][str_chat_id]:
        repost_map['TG'][str_chat_id]['targets'] = []

    if group['id'] in repost_map['TG'][str_chat_id]['targets']:
        text = f"Repost map from TG `{get_channel_title(chat)}` channel to VK `{group['name']}` group already exists."
    else:
        repost_map['TG'][str_chat_id]['targets'].append(group['id'])
        text = f"Added repost map from TG `{get_channel_title(chat)}` channel to VK `{group['name']}` group."

    settings.REPOST_MAP = repost_map
    settings.save()
    del context.user_data['ADDING_CHANNEL']

    buttons = [
        [InlineKeyboardButton(text='Configure other', callback_data=str(START))],
    ]

    update.callback_query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    return END


chat_regex = re.compile(r'^@[\w_\d]+$')

handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start, pattern='^' + str(ADD_MAP) + '$')],
    states={
        ADD_CHANNEL_ID: [MessageHandler(Filters.forwarded | Filters.regex(chat_regex), add_channel_id),
                         CallbackQueryHandler(add_channel_id, pattern='^add_map__-?[\w\d]+$')],
        ADD_PUBLIC_ID: [CallbackQueryHandler(add_group_id, pattern='^add_group__-?[\w\d]+$')],
        CANCEL: [CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$')],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    map_to_parent={
        END: START,
    }
)
