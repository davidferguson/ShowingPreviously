import re
import lxml
import datetime

from bs4 import BeautifulSoup
from typing import Tuple, Optional

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE

CHAIN = Chain('Isle of Bute Discovery Centre')
CINEMA = Cinema('Isle of Bute Discovery Centre Cinema', UK_TIMEZONE)
SCREEN = Screen('Screen 1')

FEED_URL = 'http://discoverycentrecinema.blogspot.com/feeds/posts/default'
FILM_TITLE_REGEX = re.compile(r'(?P<title>.*) (?P<rating>\(..*\))')


class InvalidRowException(Exception):
    pass


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


class IsleOfButeDiscoveryCentreCinema(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        feed_contents = get_response(FEED_URL).text
        feed_soup = BeautifulSoup(feed_contents, features='xml')
        html_contents = feed_soup.find('entry').find('content', type='html').contents
        html_soup = BeautifulSoup(html_contents[0], features='html.parser')
        listings_table = html_soup.find('table')
        for i, row in enumerate(listings_table.find_all('tr')):
            if i == 0:
                continue  # skip the 'Film listings for <Month> row'
            elif i == 1:
                check_table_schema(row)
                continue
            else:
                showings += parse_table_row(row)
        return showings


def check_table_schema(table_schema_row: BeautifulSoup):
    row_datas = [td.text for td in table_schema_row.find_all('td')]
    schema_check = \
        row_datas[0] == 'Date' and \
        row_datas[1] == 'Day' and \
        row_datas[2] == 'Film - Afternoon' and \
        row_datas[3] == 'Time' and \
        row_datas[4] == 'Film - Evening' and \
        row_datas[5] == 'Time'
    if not schema_check:
        raise CinemaArchiverException('Table schema does not match expected format')


def parse_table_row(table_row: BeautifulSoup) -> [Showing]:
    row_datas = [td.text for td in table_row.find_all('td')]
    showings = [extract_showing(row_datas, 0), extract_showing(row_datas, 1)]
    showings = [showing for showing in showings if showing is not None]
    return showings


def extract_showing(row_datas: [str], showing_number: int) -> Optional[Showing]:
    try:
        (row_date, film_name, showing_time) = get_row_details(row_datas, showing_number)
    except InvalidRowException:
        return None
    showing_film = FILM_TITLE_REGEX.search(film_name).group('title')
    showing_time = datetime.datetime.strptime(showing_time, '%I.%M%p')
    showing_timestamp = row_date + datetime.timedelta(hours=showing_time.hour, minutes=showing_time.minute)
    film = Film(name=showing_film, year='')
    showing = Showing(film, showing_timestamp, CHAIN, CINEMA, SCREEN, {})
    return showing


def get_row_details(row_datas: [str], showing_number: int) -> Tuple[datetime.datetime, str, str]:
    if len(row_datas) != 6 or row_datas[0].strip() == '':
        raise InvalidRowException()
    row_date = datetime.datetime.strptime(row_datas[0], '%d/%m/%Y')
    if showing_number == 0:
        film_name = row_datas[2]
        showing_time = row_datas[3]
    elif showing_number == 1:
        film_name = row_datas[4]
        showing_time = row_datas[5]
    else:
        raise CinemaArchiverException(f'Invalid showing number: {showing_number}')
    if film_name.strip() == '' and showing_time.strip() == '':
        raise InvalidRowException()
    return row_date, film_name, showing_time
