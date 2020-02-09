from bot.utils import get_log

from .server import init


log = get_log(__name__)


def run_server(foreground: bool = False):
    updater = init()

    if foreground:
        log.info('TG2VK starting')
        updater.idle()
    else:
        updater.start_polling()
        log.info('TG2VK starting')

