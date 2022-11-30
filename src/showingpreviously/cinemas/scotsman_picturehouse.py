from typing import Iterator

import datetime
from bs4 import BeautifulSoup

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import STANDARD_DAYS_AHEAD, UK_TIMEZONE, UNKNOWN_FILM_YEAR


FILM_EVENT_URL = 'https://scotsmanpicturehouse.co.uk/wp-admin/admin-ajax.php?action=cal_filter_vista&filter={date}'

CHAIN = Chain('Scotsman Picturehouse')
CINEMA = Cinema('Scotsman Picturehouse', UK_TIMEZONE)
SCREEN = Screen('Screen 1')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_showing_dates() -> Iterator[datetime.datetime]:
    current_date = datetime.date.today()
    end_date = current_date + datetime.timedelta(days=STANDARD_DAYS_AHEAD)
    while current_date < end_date:
        yield current_date
        current_date += datetime.timedelta(days=1)


def get_showings_for_date(date: datetime.datetime) -> [Showing]:
    showings = []
    date_str = date.strftime('%Y-%m-%d')
    date_url = FILM_EVENT_URL.format(date=date_str)
    resp = get_response(date_url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    for film_soup in soup.find_all('div', class_='films'):
        film_name = film_soup['data-movie-filter']
        film = Film(film_name, UNKNOWN_FILM_YEAR)
        for showing_soup in film_soup.find_all('div', class_='cinematimes'):
            showing_time_str = f'{date_str} {showing_soup.text}'
            showing_time = datetime.datetime.strptime(showing_time_str, '%Y-%m-%d %H:%M')
            showing = Showing(
                film=film,
                time=showing_time,
                chain=CHAIN,
                cinema=CINEMA,
                screen=SCREEN,
                json_attributes={}
            )
            showings.append(showing)
    return showings


class ScotsmanPicturehouse(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        for fetch_date in get_showing_dates():
            showings += get_showings_for_date(fetch_date)
        return showings
