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
    DEL_MAP,
    CANCEL,
    END,
    START,
    DEL_CHANNEL_ID,
    DEL_PUBLIC_ID,
)
from bot.commands._utils import require_owner
from bot.utils import get_log

from .common import cancel


log = get_log(__name__)


@require_owner
def start(update: Update, context: CallbackContext):
    log.debug('Start deleting map')

    channels = (settings.REPOST_MAP or {}).get('TG', {})

    if not channels:
        log.debug('Nothing to delete')
        button = InlineKeyboardButton(text='Configure other', callback_data=str(START))

        update.callback_query.edit_message_text(
            'Nothing to delete.',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[button]])
        )

        return END

    buttons = []
    configured = ''
    number = 0
    chats = []

    for channel in channels:
        chat = bot.get_chat(channel)
        number += 1
        chats.append(InlineKeyboardButton(text=str(number), callback_data=f'del_map__{channel}'))
        configured += f'{number}. {get_channel_title(chat)}\n'

    if chats:
        buttons.append(chats)

    buttons.append([InlineKeyboardButton(text='Cancel', callback_data=str(START))])
    keyboard = InlineKeyboardMarkup(buttons)

    text = f'Select source to change:\n\n{configured}'

    update.callback_query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    return DEL_CHANNEL_ID


@require_owner
def del_channel_id(update: Update, context: CallbackContext):
    log.debug('Deleting channel')
    text = ''
    buttons = []
    chat_id = update.callback_query.data.split('__')[-1]
    channels = (settings.REPOST_MAP or {}).get('TG', {})

    if str(chat_id) not in channels:
        log.debug('Nothing to delete')
        button = InlineKeyboardButton(text='Configure other', callback_data=str(START))

        update.callback_query.edit_message_text(
            'Source chat not configured.',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[button]])
        )

        return END

    log.debug('Source chat id `%s`.', chat_id)

    try:
        chat = bot.get_chat(chat_id)
    except TelegramError:
        log.debug('Can\'t find channel for `%s`, please try again.', chat_id)
        text = f'Can\'t find channel for `{chat_id}`, please try again.'

        update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            keyboard_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Start again', callback_data=str(DEL_MAP))]])
        )

        return DEL_MAP

    group_ids = [str(gid) for gid in channels[chat_id].get('targets', [])]

    if group_ids:
        vk_groups = Client().groups_get_by_id(group_ids=group_ids)
    else:
        vk_groups = []

    if vk_groups:
        text += f'Select group to stop reposting from `{get_channel_title(chat)}` channel.\n\n'
    else:
        del channels[chat_id]
        settings.REPOST_MAP['TG'] = channels
        settings.save()

        log.debug('All groups removed', chat_id)
        text = (f'Source channel have no accessible target VK groups. '
                f'It was removed.')

        update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            keyboard_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text='Start again', callback_data=str(DEL_MAP))]])
        )

        return DEL_MAP

    text += 'Now select target VK group:\n\n'

    context.user_data['DELETING_CHANNEL'] = chat_id
    number = 0
    groups = []

    for group in vk_groups:
        number += 1
        text += f"{number}. {group['name']}\n"
        groups.append(InlineKeyboardButton(text=f'{number}', callback_data=f"del_group__{group['id']}"))

    if groups:
        groups.append(InlineKeyboardButton(text='All', callback_data=f"del_group__all"))
        buttons.append(groups)

    buttons.append([InlineKeyboardButton(text='Cancel', callback_data=str(START))])
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    return DEL_PUBLIC_ID


@require_owner
def del_group_id(update: Update, context: CallbackContext):
    log.debug('Start deleting group')
    buttons = [
        [InlineKeyboardButton(text='Start again', callback_data=str(DEL_MAP))],
    ]

    if not context.user_data['DELETING_CHANNEL']:
        log.debug('Source channel not defined')

        update.callback_query.edit_message_text(
            'Source channel not defined',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return DEL_MAP

    group_id = update.callback_query.data.split('__')[-1]
    chat_id = context.user_data['DELETING_CHANNEL']

    try:
        chat = bot.get_chat(chat_id)
    except TelegramError:
        log.debug('Source chat not found `%s`', chat_id)

        update.callback_query.edit_message_text(
            'Source chat not found',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        return DEL_MAP

    if not group_id:
        log.debug('Target group id not defined')

        update.callback_query.edit_message_text(
            'Target group id not defined',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        return DEL_MAP

    channels = (settings.REPOST_MAP or {}).get('TG', {})
    buttons = [
        [InlineKeyboardButton(text='Configure other', callback_data=str(START))],
    ]

    if chat_id not in channels:
        log.debug('Source chat id not found in configuration')

        update.callback_query.edit_message_text(
            'Source chat id not found in configuration',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        return DEL_MAP

    if group_id == 'all':
        log.debug('Remove all groups')

        if chat_id in channels:
            del channels[chat_id]
            settings.REPOST_MAP['TG'] = channels
            settings.save()

        update.callback_query.edit_message_text(
            f'All reposting from channel `{get_channel_title(chat)}` disabled.',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        return END

    group_id = int(group_id)
    groups = channels[chat_id].get('targets', [])

    try:
        groups.remove(int(group_id))
    except ValueError:
        try:
            groups.remove(str(group_id))
        except ValueError:
            pass

    channels[chat_id]['targets'] = groups

    if not groups:
        log.debug('No groups left')
        del channels[chat_id]

    settings.REPOST_MAP['TG'] = channels

    settings.save()

    del context.user_data['DELETING_CHANNEL']

    buttons = [
        [InlineKeyboardButton(text='Configure other', callback_data=str(START))],
    ]

    update.callback_query.edit_message_text(
        'Done',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    return END


handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start, pattern='^' + str(DEL_MAP) + '$')],
    states={
        DEL_CHANNEL_ID: [CallbackQueryHandler(del_channel_id, pattern='^del_map__-?[\w\d]+$')],
        DEL_PUBLIC_ID: [CallbackQueryHandler(del_group_id, pattern='^del_group__-?[\w\d]+$')],
        CANCEL: [CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$')],
    },
    fallbacks=[CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$')],
    map_to_parent={
        END: START,
    },
    per_message=True,
)
