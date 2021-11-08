import re
import time

from bs4 import BeautifulSoup
from datetime import datetime
import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE


CINEMAS_INDEX_URL = 'https://www.merlincinemas.co.uk/'
FILM_URL = 'https://helston.merlincinemas.co.uk/ajax/film/{film_id}'
SCREEN_NAME_PATTERN = re.compile(r'Showing In&nbsp;(?P<screen_name>.+?) -')

CHAIN = Chain('Merlin Cinemas')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict() -> dict[str, Cinema]:
    r = get_response(CINEMAS_INDEX_URL)
    soup = BeautifulSoup(r.text, features='html.parser')
    cinema_list = soup.find('div', {'class': 'welcome_choice'})
    cinemas = {}
    for cinema_link in cinema_list.find_all('a', {'href': True}):
        cinema_name = cinema_link.text
        cinema_url = cinema_link['href']
        if 'regal-theatre' in cinema_url:
            continue  # skip the duplicate theatre
        cinemas[cinema_url] = Cinema(cinema_name, UK_TIMEZONE)
    return cinemas


def get_films_info(film_ids: [str]) -> dict[str, Film]:
    films = {}
    for film_id in film_ids:
        url = FILM_URL.format(film_id=film_id)
        r = get_response(url)
        soup = BeautifulSoup(r.text, features='html.parser')
        film_title = soup.find('h1').text
        try:
            released_tag = soup.find('div', {'class': 'released'})
            released_date = released_tag.find('span').text
            released_year = released_date[-4:]
        except AttributeError:
            released_year = '0'
        films[film_id] = Film(film_title, released_year)
    return films


def get_date_and_screen(booking_url: str, delay_time: int) -> (datetime, Screen):
    try:
        r = get_response(booking_url)
    except requests.exceptions.ConnectionError:
        # admit-one.eu has annoying rate limiting. try again, with an increased back-off
        delay_time += 10
        time.sleep(delay_time)
        return get_date_and_screen(booking_url, delay_time)
    soup = BeautifulSoup(r.text, features='html.parser')
    date = None
    for p in soup.find('div', {'class': 'OLCT_ticketInfoText'}).find_all('p'):
        if '@' in p.text:
            date_str = p.text.strip()
            date = datetime.strptime(date_str, '%A %d %B %Y @ %H:%M')
            break
    screen_name = SCREEN_NAME_PATTERN.search(r.text).group('screen_name')
    return date, Screen(screen_name)


def get_attributes(film_card, listing) -> dict[str, any]:
    attributes = {}
    if listing.find('img', {'data-key': 'subtitled'}) is not None:
        attributes['subtitled'] = True
    if listing.find('img', {'data-key': 'baby'}) is not None:
        attributes['carers-and-babies'] = True
    if film_card.find('img', {'class': 'live_theatre'}) is not None:
        attributes['format'] = ['Live']
    return attributes


def get_showings_date(cinema_url: str, cinema: Cinema) -> [Showing]:
    r = get_response(cinema_url)
    soup = BeautifulSoup(r.text, features='html.parser')
    full_list = soup.find('div', {'data-frame': 'full'})

    # first get the films
    film_ids = []
    for film_card in full_list.find_all('div', {'class': 'filmCard'}):
        film_ids.append(film_card['data-film'])
    films = get_films_info(film_ids)

    # now get the showings
    showings = []
    for film_card in full_list.find_all('div', {'class': 'filmCard'}):
        film = films[film_card['data-film']]
        listings_table = film_card.find('table')
        for date_row in listings_table.find_all('tr'):
            for listing in date_row.find_all('a', {'href': True}):
                listing_url = listing['href']
                date, screen = get_date_and_screen(listing_url, 0)
                json_attributes = get_attributes(film_card, listing)
                showings.append(Showing(film, date, CHAIN, cinema, screen, json_attributes))

    return showings


class Merlin(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_url, cinema in cinemas.items():
            showings += get_showings_date(cinema_url, cinema)
        return showings
