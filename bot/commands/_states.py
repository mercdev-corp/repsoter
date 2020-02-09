from telegram.ext import ConversationHandler


ADD_MAP, DEL_MAP, VK_CONNECTION, OPTION = map(chr, range(4))
APP_ID, AUTH_URL = map(chr, range(4, 6))
CANCEL, START, SKIP = map(chr, range(6, 9))
ADD_CHANNEL_ID, ADD_PUBLIC_ID, DEL_CHANNEL_ID, DEL_PUBLIC_ID = map(chr, range(9, 13))
END = ConversationHandler.END


__all__ = [
    ADD_MAP,
    DEL_MAP,
    VK_CONNECTION,
    OPTION,
    APP_ID,
    AUTH_URL,
    CANCEL,
    START,
    SKIP,
    END,
    ADD_CHANNEL_ID,
    ADD_PUBLIC_ID,
    DEL_CHANNEL_ID,
    DEL_PUBLIC_ID,
]
