import json

from datetime import datetime, timedelta
import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing


CINEMAS_API_URL = 'https://www.cineworld.co.uk/uk/data-api-service/v1/quickbook/10108/cinemas/with-event/until/{end_date}'
SHOWINGS_API_URL = 'https://www.cineworld.co.uk/uk/data-api-service/v1/quickbook/10108/film-events/in-cinema/{cinema_id}/at-date/{date}'

DAYS_AHEAD = 2
CHAIN = Chain('Cineworld UK')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict() -> dict[str, Cinema]:
    end_date = datetime.now() + timedelta(days=DAYS_AHEAD)
    url = CINEMAS_API_URL.format(end_date=end_date.strftime('%Y-%m-%d'))
    r = get_response(url)
    try:
        cinemas_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {url}')
    cinemas = {}
    for cinema in cinemas_data['body']['cinemas']:
        id = cinema['id']
        name = cinema['displayName']
        timezone = 'Europe/London'
        cinemas[id] = Cinema(name, timezone)
    return cinemas


def get_json_attributes(attributes: [str]) -> dict[str, any]:
    json_attributes = {}
    for attribute in attributes:
        if attribute == 'audio-described':
            json_attributes['audio-described'] = True
        elif attribute in ['120-fps', '35-mm', '70-mm', '4dx', '4k', 'imax', 'imax-3d', 'imax-3d-vip', 'imax-vr', 'screenx', 'thx', '3d']:
            if 'format' not in json_attributes:
                json_attributes['format'] = []
            json_attributes['format'].append(attribute)
        elif attribute in ['bengali', 'chinese-st', 'filipino', 'gujarati', 'hindi', 'japanese', 'kannada', 'korean', 'malayalam', 'mandarin', 'marathi', 'nepali', 'punjabi', 'russian', 'spanish', 'tamil', 'telugu', 'urdu', 'vietnamese']:
            json_attributes['language'] = attribute
        elif attribute in ['sub-titled', 'subbed', 'korean-sub', 'spanish-sub']:
            if attribute == 'korean-sub':
                json_attributes['subtitled'] = 'korean'
            elif attribute == 'spanish-sub':
                json_attributes['subtitled'] = 'spanish'
            else:
                json_attributes['subtitled'] = True
        elif attribute in ['dubbed', 'eng-dubbed', 'spanish-dub']:
            # these should already be handled by the language the film is in
            pass

    return json_attributes


def get_showings_date(cinema_id: str, cinema: Cinema, date: str) -> [Showing]:
    url = SHOWINGS_API_URL.format(cinema_id=cinema_id, date=date)
    r = get_response(url)
    try:
        showings_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {url}')

    films = {}
    for film in showings_data['body']['films']:
        id = film['id']
        name = film['name']
        year = film['releaseYear']
        films[id] = Film(name, year)

    showings = []
    for showing in showings_data['body']['events']:
        film = films[showing['filmId']]
        screen_name = f'Auditorium {showing["auditorium"]}'
        screen = Screen(screen_name)
        time = datetime.fromisoformat(showing['eventDateTime'])
        json_attributes = get_json_attributes(showing['attributeIds'])
        showings.append(Showing(film, time, CHAIN, cinema, screen, json_attributes))
    return showings


def get_showing_dates() -> str:
    current_date = datetime.now()
    end_date = current_date + timedelta(days=DAYS_AHEAD)
    while current_date < end_date:
        yield current_date.strftime('%Y-%m-%d')
        current_date += timedelta(days=1)


class Cineworld(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_id, cinema in cinemas.items():
            for date in get_showing_dates():
                showings += get_showings_date(cinema_id, cinema, date)
        return showings
