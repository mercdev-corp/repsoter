import argparse
import os


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start Telegram bot.')
    parser.add_argument('-f', dest='foreground', action='store_true',
                        help='run process in foreground')
    parser.add_argument('-s', dest='settings', action='store',
                        help='settings file', default='/settings.json')
    parser.add_argument('-t', dest='temp', action='store',
                        help='temp directory', default='/tg_tmp')

    args = vars(parser.parse_args())

    os.environ['TG_BOT_SETTINGS'] = os.path.realpath(args['settings'])
    os.environ['TG_BOT_TEMP'] = os.path.realpath(args['temp'])

    from bot.run import run_server
    run_server(args['foreground'])
