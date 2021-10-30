import sqlite3
import os
import json
from contextlib import closing
from datetime import datetime

from showingpreviously.consts import data_dir, DATABASE_NAME


def add_chain(chain_name: str) -> None:
    with closing(conn.cursor()) as cur:
        cur.execute('INSERT OR IGNORE INTO chains (name) values (?)', (chain_name,))
    conn.commit()


def add_cinema(chain_name: str, cinema_name: str, cinema_timezone: str) -> None:
    epoch_started_archiving = int(datetime.now().timestamp())
    with closing(conn.cursor()) as cur:
        cur.execute('INSERT OR IGNORE INTO cinemas (chainName, name, timezone, utcStartedArchiving) values (?, ?, ?, ?)', (chain_name, cinema_name, cinema_timezone, epoch_started_archiving,))
    conn.commit()


def add_screen(chain_name: str, cinema_name: str, screen_name: str) -> None:
    with closing(conn.cursor()) as cur:
        cur.execute('INSERT OR IGNORE INTO screens (chainName, cinemaName, name) values (?, ?, ?)', (chain_name, cinema_name, screen_name,))
    conn.commit()


def add_film(film_name: str, film_year: str) -> None:
    with closing(conn.cursor()) as cur:
        cur.execute('INSERT OR IGNORE INTO films (name, year) values (?, ?)', (film_name, film_year,))
    conn.commit()


def add_showing(film_name: str, film_year: str, chain_name: str, cinema_name: str, screen_name: str, time: datetime, json_attributes: str) -> None:
    epoch_time = int(time.timestamp())
    json_attributes_string = json.dumps(json_attributes)
    with closing(conn.cursor()) as cur:
        cur.execute(
            'INSERT OR REPLACE INTO showings (filmName, filmYear, chainName, cinemaName, screenName, utcTime, jsonAttributes) values (?, ?, ?, ?, ?, ?, ?)',
            (film_name, film_year, chain_name, cinema_name, screen_name, epoch_time, json_attributes_string,)
        )
    conn.commit()


def create_table() -> None:
    with closing(conn.cursor()) as cur:
        cur.execute('CREATE TABLE IF NOT EXISTS chains (name TEXT, PRIMARY KEY (name))')
        cur.execute('CREATE TABLE IF NOT EXISTS cinemas (chainName TEXT, name TEXT, timezone TEXT, utcStartedArchiving INT, PRIMARY KEY (chainName, name), FOREIGN KEY (chainName) REFERENCES chains(name))')
        cur.execute('CREATE TABLE IF NOT EXISTS screens (chainName TEXT, cinemaName TEXT, name TEXT, PRIMARY KEY (chainName, cinemaName, name), FOREIGN KEY (chainName) REFERENCES cinemas (chainName), FOREIGN KEY (cinemaName) REFERENCES cinemas (name))')
        cur.execute('CREATE TABLE IF NOT EXISTS films (name TEXT, year TEXT, PRIMARY KEY (name, year))')
        cur.execute('CREATE TABLE IF NOT EXISTS showings (filmName TEXT, filmYear TEXT, chainName TEXT, cinemaName TEXT, screenName TEXT, utcTime INT, jsonAttributes TEXT, PRIMARY KEY (filmName, filmYear, chainName, cinemaName, screenName, utcTime), FOREIGN KEY (filmName) REFERENCES films (name), FOREIGN KEY (filmYear) REFERENCES films (year), FOREIGN KEY (chainName) REFERENCES screens (chainName), FOREIGN KEY (cinemaName) REFERENCES screens (cinemaName), FOREIGN KEY (screenName) REFERENCES screens (name))')


def db_info() -> (int, int, int, int):
    with closing(conn.cursor()) as cur:
        chains_count = cur.execute('SELECT COUNT(*) FROM chains').fetchone()[0]
        cinema_count = cur.execute('SELECT COUNT(*) FROM cinemas').fetchone()[0]
        screen_count = cur.execute('SELECT COUNT(*) FROM screens').fetchone()[0]
        film_count = cur.execute('SELECT COUNT(*) FROM films').fetchone()[0]
        showing_count = cur.execute('SELECT COUNT(*) FROM showings').fetchone()[0]
    return chains_count, cinema_count, screen_count, film_count, showing_count


database_location = os.path.join(data_dir, DATABASE_NAME)
conn = sqlite3.connect(database_location)
create_table()
