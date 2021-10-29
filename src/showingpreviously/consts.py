import os

from appdirs import user_data_dir

PROGRAM_NAME = 'showingpreviously'
DATABASE_NAME = 'showtimes.db'
URL_LOG_NAME = 'url-log-%Y-%m-%d.txt'

data_dir = user_data_dir(PROGRAM_NAME)
os.makedirs(data_dir, exist_ok=True)
