from datetime import datetime, timedelta
import os
import shutil

from telegram.ext import CallbackContext, JobQueue

from bot.utils import get_log

from .client import Client
from ._utis import ParsedMessage, MEDIA_GROUP_FILE


log = get_log(__name__)


def upload():
    path = os.path.realpath(os.environ['TG_BOT_TEMP'])
    delete = []

    with os.scandir(path) as channels:
        for channel in channels:
            if channel.is_dir():
                channel_dir = os.path.join(path, channel.name)
                log.debug('Check `%s` for media groups', channel_dir)

                with os.scandir(channel_dir) as media_group:
                    for group in media_group:
                        posted = False

                        if group.is_dir():
                            dirname = os.path.join(path, channel.name, group.name)
                            log.debug('Check `%s` for uploads', dirname)
                            lock_file = os.path.join(dirname, '.lock')
                            media_group_data = os.path.join(dirname, MEDIA_GROUP_FILE)
                            data_exists = os.path.exists(media_group_data)
                            locked = os.path.exists(lock_file)

                            if data_exists and not locked:
                                age = datetime.fromtimestamp(
                                    os.stat(media_group_data).st_mtime)

                                log.debug('Media data file age is %s', age)

                                if datetime.now() - age > timedelta(seconds=30):
                                    log.debug('Upload media for %s', dirname)
                                    message = ParsedMessage()
                                    message.load_media_group(channel.name, group.name)
                                    Client().wall_post(message)
                                    posted = True

                            if posted:
                                log.debug('All posted `%s`', dirname)
                                delete.append(dirname)

    for dirname in delete:
        log.debug('Remove `%s`', dirname)
        shutil.rmtree(dirname, ignore_errors=True)


def photos_post(job_queue: JobQueue):
    def job(context: CallbackContext):
        log.debug('Start photos post job')
        upload()

    job_queue.run_repeating(job, interval=30, first=30)


ALL = [
    photos_post,
]
