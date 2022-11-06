import json

from datetime import datetime
from typing import Tuple
import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE


CINEMAS_API_URL = 'https://www.everymancinema.com/cinemas'
SHOWINGS_API_URL = 'https://movieeverymanapi.peachdigital.com/movies/13/{cinema_id}'

CHAIN = Chain('Everyman Cinemas')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict() -> dict[str, Cinema]:
    r = get_response(CINEMAS_API_URL)
    try:
        cinemas_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {CINEMAS_API_URL}')
    cinemas = {}
    for cinema in cinemas_data:
        id = cinema['CinemaId']
        name = cinema['CinemaName']
        cinemas[id] = Cinema(name, UK_TIMEZONE)
    return cinemas


def get_attributes_and_title(film_title:str) -> Tuple[str, dict[str, any]]:
    lives = ['National Theatre Live:','ROH Live:', 'ROH Encore:', 'Met Opera Encore:', 'Met Opera Live:', ]
    removals = ["Members' Preview:", '(Encore)', '+ Q&A', '+ Live Q&A', 'UK Jewish Film:']
    attributes = {'format':[]}

    if '(35mm)' in film_title:
        film_title = film_title.replace('(35mm)', '')
        attributes['format'].append('35mm')

    for live in lives:
        if live in film_title:
            film_title = film_title.replace(live, '')
            if 'live' not in attributes['format']:
                attributes['format'].append('live')

    for removal in removals:
        if removal in film_title:
            film_title = film_title.replace(removal, '')

    return film_title, attributes


def get_showings_date(cinema_id: str, cinema: Cinema) -> [Showing]:
    url = SHOWINGS_API_URL.format(cinema_id=cinema_id)
    r = get_response(url)
    try:
        showings_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {url}')

    showings = []
    for film_data in showings_data:
        film_title = film_data['Title']
        film_year = film_data['ReleaseDate'][:4]
        film_name, film_attributes = get_attributes_and_title(film_title)
        film = Film(film_name, film_year)
        for session in film_data['Sessions']:
            date = session['NewDate']
            for showing in session['Times']:
                screen = Screen(showing['Screen'])
                time = showing['StartTime']
                date_and_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %I:%M %p')
                showings.append(Showing(film, date_and_time, CHAIN, cinema, screen, film_attributes))
    return showings


class Everyman(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_id, cinema in cinemas.items():
            showings += get_showings_date(cinema_id, cinema)
        return showings
