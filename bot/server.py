from telegram import Bot
from telegram.ext import Dispatcher, JobQueue, Updater

from bot.utils import get_log

from .commands import ALL
from .settings import settings
from .vk.jobs import ALL as VK_JOBS


log = get_log(__name__)

dispatcher: Dispatcher = None
job_queue: JobQueue = None
updater: Updater = None


def add_handlers(dispatcher: Dispatcher):
    for cmd in ALL:
        log.debug('Register command `%s`', cmd.__name__)
        dispatcher.add_handler(getattr(cmd, 'handler'))

        error = getattr(cmd, 'error_handler', None)

        if error is not None:
            log.debug('Register error handler `%s`', error.__name__)
            dispatcher.add_error_handler(error)


def add_jobs(job_queue: JobQueue):
    for cmd in VK_JOBS:
        cmd(job_queue)


def init():
    global job_queue, dispatcher, updater

    updater = Updater(token=settings.TG_BOT_TOKEN, request_kwargs=settings.REQUEST_KWARGS, use_context=True)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue
    settings.save()

    add_handlers(dispatcher)
    add_jobs(job_queue)

    return updater
