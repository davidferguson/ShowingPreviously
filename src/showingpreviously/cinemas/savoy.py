import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE, UNKNOWN_FILM_YEAR, STANDARD_DAYS_AHEAD


CINEMAS_URL = 'http://www.savoycinemas.co.uk/'
CHAIN = Chain('Savoy Cinemas')
EVENTS_INLINE_PATTERN = re.compile(r'var\s+eventsInline\s*=\s*(?P<events_inline>(?:.|\n|\r)*?]);')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def parse_film_name(name: str) -> (str, [str]):
    attributes = {'format': []}
    # ending
    for removal in [' U', '(PG)', '(12A)', '(12)', '(15)', '(18)', '2D', '3D', '4K', '(WITH SANTA)']:
        if name.lower().endswith(removal.lower()):
            name = name[:-1 * len(removal)].strip()
            if removal in ['2D', '3D', '4K']:
                attributes['format'].append(removal)
    # starting
    for removal in ['NATIONAL THEATRE LIVE:']:
        if name.lower().startswith(removal.lower()):
            name = name[len(removal):].strip()
            if removal == 'NATIONAL THEATRE LIVE:':
                attributes['format'].append('live')
                attributes['event'] = True
    if len(attributes['format']) == 0:
        del attributes['format']
    return name, attributes


def get_cinemas_as_dict() -> dict[str, Cinema]:
    r = get_response(CINEMAS_URL)
    soup = BeautifulSoup(r.text, features='html.parser')
    cinemas = {}
    for cinema_link in soup.find_all('a', {'href': True}):
        cinema_url = cinema_link['href']
        cinema_name = cinema_link.find('div', {'class': 'title'}).text
        cinemas[cinema_url] = Cinema(cinema_name, UK_TIMEZONE)
    return cinemas


def get_attributes(showing: dict[str, any], attributes) -> dict[str, any]:
    if showing['PB'] != 'N':
        attributes['carers-and-babies'] = True
    if showing['SS'] != 'N':
        attributes['senior'] = True
    return attributes


def get_screen_inline(booking_url: str) -> Screen:
    r = requests.get(booking_url)
    soup = BeautifulSoup(r.text, features='html.parser')
    programme = soup.find('div', {'class': 'programme'})
    info = programme.find('div', {'class': 'ninecol'})
    screen_name = info.find('p').text
    return Screen(screen_name)


def get_showings_inline(cinema_url: str, cinema: Cinema, home_r: requests.Response):
    last_day = datetime.now() + timedelta(days=STANDARD_DAYS_AHEAD)
    events_json = EVENTS_INLINE_PATTERN.search(home_r.text).group('events_inline')
    try:
        events_data = json.loads(events_json)
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from JSON {events_json}')

    showings = []
    for showing in events_data:
        date_and_time = datetime.strptime(showing['date'], '%Y-%m-%d %H:%M:%S')
        if date_and_time > last_day:
            continue
        film_name, attributes = parse_film_name(showing['title'])
        film = Film(film_name, UNKNOWN_FILM_YEAR)
        booking_url = home_r.url.replace('Home', showing['bookingurl'])
        screen = get_screen_inline(booking_url)
        showings.append(Showing(film, date_and_time, CHAIN, cinema, screen, attributes))

    return showings


def get_showings_date(cinema_url: str, cinema: Cinema) -> [Showing]:
    r = get_response(cinema_url)
    soup = BeautifulSoup(r.text, features='html.parser')
    events_script = soup.find('script', string=lambda string: string and 'var Events' in string)

    if events_script is None:
        # this is the weird Corby cinema that does things differently
        return get_showings_inline(cinema_url, cinema, r)

    events_json = events_script.string.replace('var Events =', '')
    try:
        events_data = json.loads(events_json)
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from json {events_json}')

    showings = []
    for film_data in events_data['Events']:
        film_name = film_data['Title']
        film_name, json_attributes = parse_film_name(film_name)
        film_year = film_data['Year'] if film_data['Year'] != '' else UNKNOWN_FILM_YEAR
        film = Film(film_name, film_year)
        for showing in film_data['Performances']:
            date = showing['StartDate']
            screen = Screen(showing['AuditoriumName'])
            time = showing['StartTime']
            date_and_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H%M')
            json_attributes = get_attributes(showing, json_attributes)
            showings.append(Showing(film, date_and_time, CHAIN, cinema, screen, json_attributes))
    return showings


class Savoy(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_url, cinema in cinemas.items():
            showings += get_showings_date(cinema_url, cinema)
        return showings
