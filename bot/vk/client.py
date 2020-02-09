import json
import os

from telegram import Message
from requests import request
from urllib.parse import urlencode, urlparse

from bot.settings import settings
from bot.utils import get_log, log_message
from ._utis import ParsedMessage
from .exception import VKRequestError


log = get_log(__name__)
URL = 'https://api.vk.com/method'
AUTH_URL = 'https://oauth.vk.com/authorize'
VK_AUTH_REDIRECT = 'https://oauth.vk.com/blank.html'
VER = '5.103'
VK_FILES_UPLOAD_LIMIT = 5


class Client:
    token: str = None
    app_id: str = None
    _wall_id: str = ''
    group_id: str = None
    message: ParsedMessage = None

    def __init__(self):
        self.config()

    @property
    def wall_id(self):
        return self._wall_id

    @wall_id.setter
    def wall_id(self, val: str):
        self._wall_id = val
        self.group_id = val.replace('-', '')

    def config(self):
        self.app_id = settings.VK_APP_ID
        self.token = settings.VK_APP_TOKEN

    @property
    def targets(self):
        if not self.message or not self.message.src:
            log.debug('Src chat not defined')
            return []

        allowed = settings.REPOST_MAP or {}
        channel = allowed.get('TG', {}).get(str(self.message.src), {})

        targets = channel.get('targets', [])

        if not targets:
            log.debug('Map to target group not defined %s', channel)

        return targets

    @property
    def is_configured(self):
        return self.token

    def build_url(self, api_method: str, query: dict = None) -> str:
        url = urlparse(URL)
        params = {
            'v': VER,
            'access_token': self.token,
        }

        path = url.path + '/' + api_method
        url = url._replace(path=path)

        if isinstance(query, dict):
            params.update(query)

        url = url._replace(query=urlencode(params))

        return url.geturl()

    @property
    def auth_url(self) -> str:
        params = {
            'client_id': settings.VK_APP_ID,
            'redirect_uri': VK_AUTH_REDIRECT,
            'display': 'page',
            'scope': 'audio,offline,photos,video,wall',
            'response_type': 'token',
        }

        url = urlparse(AUTH_URL)
        url = url._replace(query=urlencode(params))

        return url.geturl()

    def groups_get(self, user_id: str = None) -> [dict, None]:
        params = {
            'extended': 1,
            'filter': 'admin,editor,moder,advertiser',
        }

        if user_id:
            params['user_id'] = user_id

        return self.api_req('GET', 'groups.get', params=params)

    def groups_get_by_id(self, group_id: str = None, group_ids: [str] = None) -> [dict, None]:
        params = {}

        if group_id:
            params['group_id'] = group_id
        elif group_ids:
            params['group_ids'] = ','.join(group_ids)
        else:
            return

        return self.api_req('GET', 'groups.getById', params=params)

    def video_save(self, video: dict, album: dict = None) -> dict:
        params = {
            'group_id': self.group_id,
            'from_group': 1,
            'wallpost': 0,
            'is_private': 0,
            'privacy_view': 'all',
            'privacy_comment': 'all',
            'no_comments': 0,
            'repeat': 0,
        }

        data = {
            'name': video['title'],
            'link': video['url'],
            'description': video['description'],
        }

        if album:
            params['album_id'] = album['album_id']

        resp = self.api_req('POST', 'video.save', params=params, data=data)

        request('GET', resp['upload_url'])

        return resp

    def video_add_album(self, title: str = '') -> [dict, None]:
        params = {
            'group_id': self.group_id,
            'privacy': 'all',
        }

        data = {
            'title': title,
        }

        return self.api_req('POST', 'video.addAlbum', params=params, data=data)

    def _get_photos_album(self) -> dict:
        wall_id = str(self.wall_id)

        if not settings.VK_PHOTO_ALBUM:
            settings.VK_PHOTO_ALBUM = {}

        if wall_id not in settings.VK_PHOTO_ALBUM:
            albums = self.photos_get_albums()

            if albums['count']:
                settings.VK_PHOTO_ALBUM[wall_id] = albums['items'][-1]
            else:
                settings.VK_PHOTO_ALBUM[wall_id] = self.photos_create_album()

            settings.save()

        return settings.VK_PHOTO_ALBUM[wall_id]

    def photos_get_albums(self) -> [dict, None]:
        params = {
            'group_id': self.group_id,
            'need_system': 1,
        }

        return self.api_req('GET', 'photos.getAlbums', params=params)

    def photos_create_album(self) -> [dict, None]:
        params = {
            'group_id': self.group_id,
            'title': 'PG channel photos',
            'privacy_view': 'all',
            'privacy_comment': 'all',
            'upload_by_admins_only': 1,
            'comments_disabled': 1,
        }

        data = {
            'description': 'TG to VK photos upload',
        }

        return self.api_req('POST', 'photos.createAlbum', params=params, data=data)

    def photos_get_upload_server(self, album: dict = None) -> [dict, None]:
        if not album:
            album = self._get_photos_album()

        params = {
            'group_id': self.group_id,
            'album_id': album['id'],
        }

        return self.api_req('GET', 'photos.getUploadServer', params=params)

    def photos_save(self, message: ParsedMessage) -> [dict, None]:
        if not message.photo:
            return

        photos = []

        for photo in message.photo:
            server = self.photos_get_upload_server()
            files = self.send_files(server['upload_url'], [photo])

            if not files or files['photos_list'] == '[]':
                continue

            params = {
                'group_id': self.group_id,
                'server': files['server'],
                'hash': files['hash'],
                'album_id': files['aid'],
            }

            data = {
                'photos_list': files['photos_list'],
            }

            if caption := photo.get('caption', ''):
                data['caption'] = caption

            photos += self.api_req('POST', 'photos.save', params=params, data=data)

        return photos

    def _upload_attachments(self, message: ParsedMessage, data: dict) -> dict:
        attachments = data.get('attachments', '') or []

        if attachments:
            attachments = [attachments]

        if message.url:
            attachments.append(message.url[0])

        for video in message.video:
            video = self.video_save(video)
            attachments.append(f"video{self.wall_id}_{video['video_id']}")

        if message.photo and not message.media_group:
            photos = self.photos_save(message)

            for photo in photos:
                attachments.append(f"photo{photo['owner_id']}_{photo['id']}")

        if attachments:
            data['attachments'] = ','.join(attachments)

        return data

    def _wall_post(self, message: ParsedMessage) -> [dict, None]:
        data = self._upload_attachments(message, {})

        text = message.text or message.caption

        if message.media_group or not text and not data.get('attachments', None):
            return

        params = {
            'owner_id': self.wall_id,
            'from_group': 1,
        }

        data['message'] = text

        return self.api_req('POST', 'wall.post', params=params, data=data)

    def wall_post(self, message: [Message, ParsedMessage] = None) -> [dict, None]:
        if not message:
            return

        self.message = isinstance(message, Message) and ParsedMessage(message) or message
        targets = self.targets

        if not targets:
            return

        resp = {}

        for target in targets:
            self.wall_id = str(target).strip()

            if not self.wall_id.startswith('-'):
                self.wall_id = '-' + self.wall_id

            try:
                resp[self.wall_id] = self._wall_post(self.message)
            except VKRequestError as e:
                log_message(f'Error media post: `{e}`', 'error')

        if not self.message.media_group:
            self.message.remove_files()

        return resp

    def users_get(self) -> [dict, None]:
        return self.api_req('GET', 'users.get')

    def api_req(self, method: str, api_method: str, params: dict = None, data: dict = None) -> [dict, None]:
        if not self.is_configured:
            log.debug('VK client not configured')

            return

        url = self.build_url(api_method=api_method, query=params)

        return self.req(method=method, url=url, data=data)

    def _chunk_files(self, files: list):
        for i in range(0, len(files), VK_FILES_UPLOAD_LIMIT):
            yield files[i:i + VK_FILES_UPLOAD_LIMIT]

    def send_files(self, url: str, files: list) -> [dict, None]:
        _files = {}
        count = 0

        for i in range(len(files)):
            filename = files[i]['filename']

            if not os.path.exists(filename):
                log.debug('File not found `%s`', filename)
                continue

            count += 1
            _files[f'file{count}'] = open(filename, 'rb')

        if _files:
            resp = self.req(method='POST', url=url, files=_files)
        else:
            log.debug('Upload list is empty')
            resp = {}

        for key in _files:
            _files[key].close()

        return resp

    def req(self, method: str, url: str, data: dict = None, files: dict = None) -> [dict, None]:
        log.debug('Request URL `%s` with data:\n%s\n... files:\n%s', url, data, files)

        resp = request(method=method, url=url, data=data, files=files)
        resp.raise_for_status()

        try:
            resp_data = resp.json()
        except json.JSONDecodeError as e:
            log.debug('Resp text `%s`', resp.text)
            raise e

        log.debug('Done `%s` request to `%s` with result:\n%s', method, url, resp_data)

        if 'error' in resp_data:
            log.error('Request error:\n%s', resp_data)

            raise VKRequestError(f'Error `{url}` {method} request: {resp_data}')

        return resp_data.get('response', resp_data)
