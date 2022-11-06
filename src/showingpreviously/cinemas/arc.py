import re
import time
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Tuple

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Film, Showing, Screen
from showingpreviously.consts import UK_TIMEZONE, UNKNOWN_FILM_YEAR


CINEMAS_INDEX_URL = 'http://arccinema.ie/'
SHOWING_LIST_URL = '{cinema_url}/?dIndex={date_code}'
FILM_URL = 'https://helston.merlincinemas.co.uk/ajax/film/{film_id}'
SCREEN_NAME_PATTERN = re.compile(r'Showing In&nbsp;(?P<screen_name>.+?) -')
SCREENING_FINISHED_TEXT = 'The performance has expired, or been taken off sale'
SCREENING_NO_EVENTS_TEXT = 'No event exists for the specified event code.'

CHAIN = Chain('ARC Cinema')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict() -> dict[str, Cinema]:
    r = get_response(CINEMAS_INDEX_URL)
    soup = BeautifulSoup(r.text, features='html.parser')
    cinema_list = soup.find('div', {'class': 'links'})
    cinemas = {}
    for cinema_link in cinema_list.find_all('a', {'href': True}):
        cinema_name = cinema_link.text
        cinema_url = cinema_link['href']
        cinemas[cinema_url] = Cinema(cinema_name, UK_TIMEZONE)
    return cinemas


def get_date_and_screen(booking_url: str, delay_time: int) -> (datetime, Screen):
    try:
        r = get_response(booking_url)
    except requests.exceptions.ConnectionError:
        # admit-one.eu has annoying rate limiting. try again, with an increased back-off
        delay_time += 10
        time.sleep(delay_time)
        return get_date_and_screen(booking_url, delay_time)
    if SCREENING_FINISHED_TEXT in r.text or SCREENING_NO_EVENTS_TEXT in r.text:
        # the screening has ended, and we can't get the screen name. return nothing
        return None, None
    soup = BeautifulSoup(r.text, features='html.parser')
    date_str = soup.find('p', {'id': 'OLCT_movieSynopsis'}).text
    date = datetime.strptime(date_str, '%A %d %B %Y @ %H:%M')
    screen_name = SCREEN_NAME_PATTERN.search(r.text).group('screen_name')
    return date, Screen(screen_name)


def get_film_attributes(film_title: str) -> Tuple[str, dict[str, any]]:
    attributes = {}
    if '(Subtitled)' in film_title:
        film_title = film_title.replace('(Subtitled)', '')
        attributes['subtitled'] = True
    if '- Subtitled' in film_title:
        film_title = film_title.replace('- Subtitled', '')
        attributes['subtitled'] = True
    if '- Dubbed' in film_title:
        film_title = film_title.replace('- Dubbed', '')
        attributes['language'] = 'English'
    return film_title, attributes


def get_showings_date(cinema_url: str, cinema: Cinema) -> [Showing]:
    showings = []
    for date_code in range(0, 2):
        url = SHOWING_LIST_URL.format(cinema_url=cinema_url, date_code=date_code)
        r = get_response(url)
        soup = BeautifulSoup(r.text, features='html.parser')
        full_list = soup.find('div', {'class': '_spaceOverride'})
        for film_card in full_list.find_all('div', {'class': 'a1-split100'}):
            film_info = film_card.find('div', {'class': 'movieItemDetails'})
            film_title = film_info.find('h3', {'class': 'movieItemTitle'}).text
            film_title, attributes = get_film_attributes(film_title)
            film = Film(film_title, UNKNOWN_FILM_YEAR)
            for booking_link in film_card.find_all('a', href=lambda href: href and 'admit-one.eu/?p=tickets' in href):
                link = booking_link['href']
                date, screen = get_date_and_screen(link, 0)
                if date is None or screen is None:
                    # the screening has expired, we can't do anything with it
                    continue
                showings.append(Showing(film, date, CHAIN, cinema, screen, attributes))
    return showings


class ARC(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_url, cinema in cinemas.items():
            showings += get_showings_date(cinema_url, cinema)
        return showings
