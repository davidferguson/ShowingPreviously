import os

from appdirs import user_data_dir

from showingpreviously.model import Screen


# logging consts
PROGRAM_NAME = 'showingpreviously'
DATABASE_NAME = 'showtimes.db'
URL_LOG_NAME = 'url-log-%Y-%m-%d.txt'
DATA_DIR = user_data_dir(PROGRAM_NAME)
os.makedirs(DATA_DIR, exist_ok=True)

# model consts
UNKNOWN_SCREEN = Screen('UNKNOWN SCREEN')
UNKNOWN_FILM_YEAR = ''

# archiver consts
STANDARD_DAYS_AHEAD = 2
UK_TIMEZONE = 'Europe/London'
