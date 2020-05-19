import configparser
import os


def get_csrf() -> str:
    config = configparser.ConfigParser()

    if os.path.exists('config.ini'):
        config.read('config.ini')
        csrf = config['FORM']['CSRF']
    else:
        csrf = os.environ['CSRF']

    return csrf
