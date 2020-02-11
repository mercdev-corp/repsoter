import json
import re
import os

from opengraph.opengraph import OpenGraph
from telegram import File, Message, MessageEntity

from bot.utils import get_log


log = get_log(__name__)
VK_VIDEO_RE: re.Pattern = re.compile(
    r'^'
    r'(?:https?://)?'
    r'(?:www\.)?'
    r'(?:'
    r'(?:youtube.com/(?:v/|embed/|watch))'
    r'|youtu.be/\w+'
    r'|vimeo.com/\d+'
    r'|twitch.tv/videos/\d+'
    # r'|mixer.com/\w+\?clip'
    r').*$'
)
TEXT_LINK_TEMPLATE = '{}'
MEDIA_GROUP_FILE = 'media_group.json'
EXT = {
    'photo': '.jpg',
    'audio': '.mp3',
    'video': '.mp4',
}
MEDIA_TYPES = ['animation', 'photo', 'video', 'audio', 'file']


class ParsedMessage:
    message: Message = None
    src: int = 0
    media_group: int = ''
    text: str = None
    caption: str = None
    animation: list = None
    video: list = None
    photo: list = None
    audio: list = None
    file: list = None
    url: list = None

    def __init__(self, message: Message = None):
        self.text = ''
        self.caption = ''
        self.animation = []
        self.video = []
        self.photo = []
        self.audio = []
        self.file = []
        self.url = []

        if message:
            self.message = message
            self.src = message.chat_id
            self.media_group = message.media_group_id or ''
            self.parse()

    def _is_video(self, url: str) -> [dict, None]:
        log.debug('Detect if `%s` is video URL', url)

        if VK_VIDEO_RE.search(url):
            data = {
                'url': url,
                'title': 'video',
                'description': '',
            }
            resp = OpenGraph(url=url, scrape=True)
            log.debug('OpenGraph for `%s` is:\n%s', url, resp)

            if resp.is_valid():
                data['title'] = resp.get('title', resp.get('video:title', data['url']))
                data['description'] = resp.get('description', resp.get('video:description', data['url']))

            log.debug('URL `%s` defined as video', url)
            return data
        else:
            log.debug('URL `%s` not match video regex', url)

    def parse_photo(self):
        if not self.message.photo:
            return

        file = self.message.photo[-1].get_file()
        self.download_file(file, 'photo')

    def download_file(self, file: File, content_type: str):
        custom_path = os.environ['TG_BOT_TEMP']

        if self.media_group:
            custom_path = os.path.join(custom_path, str(self.message.chat_id),
                                       str(self.message.media_group_id))

        custom_path = os.path.realpath(custom_path)
        os.makedirs(custom_path, exist_ok=True)

        lock_file = os.path.join(custom_path, '.lock')

        if not os.path.exists(lock_file):
            open(lock_file, 'wt').close()

        basename = file.file_path and os.path.basename(file.file_path) or EXT[content_type]
        file_path = os.path.join(custom_path,  f'{file.file_id}_{basename}')
        filename = file.download(custom_path=file_path)

        log.debug('File downloaded to dir `%s` filename `%s`', custom_path, filename)

        data = {
            'type': content_type,
            'filename': filename,
            'caption': self.caption,
        }

        if self.media_group:
            json_file_path = os.path.join(custom_path, MEDIA_GROUP_FILE)
            json_dump = []

            if os.path.exists(json_file_path):
                with open(json_file_path, 'rt') as json_file:
                    json_dump = json.load(json_file)

            with open(json_file_path, 'wt') as json_file:
                json_dump.append(data)
                json.dump(json_dump, json_file, indent=4)

        setattr(self, content_type, [data])
        os.remove(lock_file)

    def load_media_group(self, channel_id: str, media_group_id: str):
        self.src = channel_id
        json_file = os.path.join(os.environ['TG_BOT_TEMP'], channel_id,
                                 media_group_id, MEDIA_GROUP_FILE)
        json_file = os.path.realpath(json_file)

        if not os.path.exists(json_file):
            return

        with open(json_file) as media_data:
            for entry in json.load(media_data):
                if entry['type'] in MEDIA_TYPES:
                    getattr(self, entry['type']).append(entry)

    def remove_files(self):
        for media in MEDIA_TYPES:
            for entry in getattr(self, media):
                if filename := entry.get('filename', ''):
                    try:
                        os.remove(filename)
                    except FileNotFoundError:
                        pass

    def parse_url(self):
        shift = 0
        entities = self.message.entities or self.message.caption_entities
        original = self.text or self.caption
        text = original

        for entry in entities:
            if entry.type in [MessageEntity.URL, MessageEntity.TEXT_LINK]:
                if entry.type == MessageEntity.TEXT_LINK:
                    url = entry.url
                else:
                    url = (original[entry.offset:entry.offset + entry.length])

                video_data = self._is_video(url)

                if video_data:
                    self.video.append(video_data)
                else:
                    self.url.append(url)

                if entry.type == MessageEntity.TEXT_LINK:
                    url = TEXT_LINK_TEMPLATE.format(url)
                    point = entry.offset + entry.length + shift

                    text = text[:point] + ' ' + url + text[point:]
                    shift += len(url) + 1

        if self.text:
            self.text = text
        else:
            self.caption = text

    def parse(self):
        self.text = self.message.text or ''
        self.caption = self.message.caption or ''

        self.parse_photo()
        self.parse_url()
