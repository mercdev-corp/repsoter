# Telegram bot for automatic reposting from TG channel to VK group wall

**Requirements:**

You need to have `Docker` and `Docker Compose` on your server to run bot using Docker.

Or you need use `Python 3.8` to run bot directly.

## Features

- Basic security (allow commands only from owner)
- Repost text.
- Reformat marked text (insert visible links back).
- Detect video links and post it as video on VK (require enabled video gallery on target VK group).
- Upload photo and groups of photos and post it (require enabled photo gallery on target VK group).
- Add general link from text as attachments to show preview on VK.

## Execution

**Docker**

Go to `docker` directory in repository and run `docker-compose up -d` command

**Native**

Go to repository's directory and run `python3.8 bot.py -s "./docker/settings.json" -t "./tmp"` command.

## Setup

Clone repository to your server. Copy `docker/settings.json.example` to `docker/settings.json`.

1. Create new bot in [@BotFather](https://t.me/BotFather). If you want to enable group messages reading also — disable privacy mode here before you'll add bot to target group!

2. Add bot to target telegram channel. Only then it'll get all updates from this channels.

3. Replace `"TG_BOT_TOKEN"` value with one you've get from [@BotFather](https://t.me/BotFather) in `docker/settings.json`.

    Also fill `"PASSWORD"` you wish in `docker/settings.json`.

4. Go to `docker` folder and execute bot with `docker-compose up -d` command.

5. Find bot in Telegram application and send `/start` command in chat. Bot will ask you for password. Answer with `"PASSWORD"` value you've stored in `docker/settings.json` file at 3rd step.

6. Create new **standalone** app here [https://vk.com/editapp?act=create] if you have not one already. Publishing of your application is not necessary.

7. Send `/config` command to bot and follow steps to setup connection to VK. 

8. Send `/config` again to setup routes for reposting from TG channels to VK groups.
