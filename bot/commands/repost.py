import logging
import json

from telegram import Update
from telegram.ext import MessageHandler, Filters, CallbackContext

from bot.vk.client import Client
from bot.utils import get_log

from ._utils import check_source, log_message


log = get_log(__name__)


@check_source
def command(update: Update, context: CallbackContext):
    log.debug('Repost channel message')

    if log.getEffectiveLevel() == logging.DEBUG:
        log.debug('Message:\n%s', json.dumps(update.to_dict(), indent=4))
        # log.debug('Context:\n%s', json.dumps(json.loads(str(context)), indent=4))

    client = Client()
    resp = client.wall_post(message=update.effective_message)

    if resp is None:
        level = 'error'
        text = f""""Message not reposted:

```
{update.effective_message.text}
{update.effective_message.caption}
```

```
{resp}
```
"""

        if not client.is_configured:
            text += '\n\nVK connection not configured. Send /config to configure it.'
    else:
        level = ''
        text = f"""Message is reposted:

```
{update.effective_message.text}
{update.effective_message.caption}
```

Response:

```
{json.dumps(resp, indent=4)}
```
"""

    log_message(text, level)


handler = MessageHandler(Filters.update.channel_posts &
                         ~ (Filters.update.edited_channel_post
                            | Filters.update.edited_message), command)
