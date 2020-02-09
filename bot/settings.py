import logging
import json
import os

from bot.utils import get_log

from .utils import parse_proxy_url


log = get_log(__name__)
_settings = {}


class Settings:
    _filename = '/settings.json'
    _init = True

    def __init__(self):
        self._filename = os.environ.get('TG_BOT_SETTINGS', '/settings.json')

    def update(self, new_settings: dict):
        _settings.update(new_settings)

    def __getitem__(self, item: str):
        return _settings.get(item, None)

    def __getattr__(self, item: str):
        if item in dir(self):
            return super(Settings, self).__getattr__(item)

        if item in _settings:
            return _settings[item]

    def __setitem__(self, key, value):
        _settings[key] = value

        self.save()

    def __setattr__(self, key, value):
        if key in dir(self):
            return super(Settings, self).__setattr__(key, value)

        self[key] = value

        super(Settings, self).__setattr__(key, value)

    def load(self):
        with open(self._filename, 'r') as fp:
            _settings.update(json.load(fp=fp))

        if _settings['PROXY'] and not _settings['REQUEST_KWARGS']:
            url, kwargs = parse_proxy_url(_settings['PROXY'])

            if kwargs:
                _settings['PROXY'] = url
                _settings['REQUEST_KWARGS'] = {
                    'proxy_url': url,
                    'urllib3_proxy_kwargs': kwargs
                }

        logging.basicConfig(
            format=_settings['LOGGING_FORMAT'],
            level=getattr(logging, _settings['LOGGING_LEVEL'], 'ERROR')
        )
        self._init = False
        log.debug('Use settings file `%s`', self._filename)

    def save(self):
        if self._init:
            return

        log.debug('Save settings')

        with open(self._filename, 'w') as fp:
            json.dump(_settings, fp=fp, indent=4)


settings = Settings()

settings.PROXY = None
settings.REQUEST_KWARGS = None
settings.LOGGING_LEVEL = 'ERROR'
settings.LOGGING_FORMAT = '>>> %(asctime)s [%(levelname)s] %(name)s:%(lineno)d\n... %(funcName)s: %(message)s'

settings.load()

