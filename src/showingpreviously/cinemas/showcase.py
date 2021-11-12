import json
import re

from datetime import datetime
import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE


CINEMAS_URL = 'https://www.showcasecinemas.co.uk'
SHOWINGS_API_URL = 'https://movieapi.showcasecinemas.co.uk/movies/45/{cinema_id}?expandGenres=true&splitByAttributes=true'

CINEMAS_LIST_PATTERN = re.compile(r'\'list\':\s*(?P<cinemas_list>\[.+?])\s*}')

CHAIN = Chain('Showcase Cinemas')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict() -> dict[str, Cinema]:
    r = get_response(CINEMAS_URL)
    cinemas_str = CINEMAS_LIST_PATTERN.search(r.text).group('cinemas_list')
    try:
        cinemas_data = json.loads(cinemas_str)
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {CINEMAS_URL}')
    cinemas = {}
    for cinema in cinemas_data:
        id = cinema['CinemaId']
        name = cinema['CinemaName']
        cinemas[id] = Cinema(name, UK_TIMEZONE)
    return cinemas


def get_attributes(experiences: [dict[str, any]]) -> dict[str, any]:
    attributes = {'format': []}
    for experience in experiences:
        if experience['ExternalId'] == 'AD':
            attributes['audio-described'] = True
        elif experience['ExternalId'] == 'Event':
            attributes['event'] = True
        elif experience['ExternalId'] in ['Baby Pic', 'Baby Cin']:
            attributes['carers-and-babies'] = True
        elif experience['ExternalId'] in ['XP', 'Real D 3D', 'IMAX', 'IMAX 2D', 'IMAX 3D', 'LVS', '3D+ HFR']:
            attributes['format'].append(experience['ExternalId'])
        elif experience['ExternalId'] == 'XPL':
            attributes['format'].append('XP')
            attributes['format'].append('Atmos')
        elif experience['ExternalId'] == '3DS':
            attributes['format'].append('3D')
            # don't want to overwrite a more detailed attribute
            if 'subtitled' not in attributes:
                attributes['subtitled'] = True
        elif experience['ExternalId'] == 'X3D':
            attributes['format'].append('XP')
            attributes['format'].append('3D')
            attributes['format'].append('Atmos')
        elif experience['ExternalId'] == 'DOLA':
            attributes['format'].append('Atmos')
        # subtitled
        elif experience['ExternalId'] == 'Subtitled':
            # don't want to overwrite a more detailed attribute
            if 'subtitled' not in attributes:
                attributes['subtitled'] = True
        elif experience['ExternalId'] == 'POLSB':
            attributes['language'] = 'English'
            attributes['subtitled'] = 'Polish'
        # different languages, no subtitle
        elif experience['ExternalId'] == 'RUSSIAN':
            attributes['language'] = 'Russian'
        elif experience['ExternalId'] == 'DBE':
            attributes['language'] = 'English'
        elif experience['ExternalId'] == 'DBH':
            attributes['language'] = 'Hindi'
        elif experience['ExternalId'] == 'In Hindi':
            attributes['language'] = 'Hindi'
        # dubbed languages, with subtitle
        elif experience['ExternalId'] == 'JPE':
            attributes['language'] = 'Japanese'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'FRE':
            attributes['language'] = 'French'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'KORE':
            attributes['language'] = 'Korean'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'POE':
            attributes['language'] = 'Polish'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'CANTON':
            attributes['language'] = 'Cantonese'
            attributes['subtitled'] = 'Chinese and English'
        elif experience['ExternalId'] == 'MANE':
            attributes['language'] = 'Mandarin'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'TAMEN':
            attributes['language'] = 'Tamil'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'MALAY':
            attributes['language'] = 'Malayalam'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'HIE':
            attributes['language'] = 'Hindi'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'FL-NPE':
            attributes['language'] = 'Nepali'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'DANE':
            attributes['language'] = 'Danish'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'RUSE':
            attributes['language'] = 'Russian'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'ROME':
            attributes['language'] = 'Romanian'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'LATV':
            attributes['language'] = 'Latvian'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'ITALIAN':
            attributes['language'] = 'Italian'
            attributes['subtitled'] = 'English'
        elif experience['ExternalId'] == 'HEBREW':
            attributes['language'] = 'Hebrew'
            attributes['subtitled'] = 'English'

    if len(attributes['format']) == 0:
        del attributes['format']
    return attributes


def get_showings_date(cinema_id: str, cinema: Cinema) -> [Showing]:
    url = SHOWINGS_API_URL.format(cinema_id=cinema_id)
    r = get_response(url)
    try:
        showings_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {url}')

    showings = []
    for film_data in showings_data:
        film_name = film_data['Title']
        film_release_date = film_data['ReleaseDate']
        film_year = str(datetime.fromisoformat(film_release_date).year)
        film = Film(film_name, film_year)
        for showing_day in film_data['Sessions']:
            date = showing_day['NewDate']
            for experience in showing_day['ExperienceTypes']:
                for showing in experience['Times']:
                    screen = Screen(showing['Screen'])
                    time = showing['StartTime']
                    date_and_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %I:%M %p')
                    json_attributes = get_attributes(showing['Experience'])
                    showings.append(Showing(film, date_and_time, CHAIN, cinema, screen, json_attributes))
    return showings


class Showcase(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_id, cinema in cinemas.items():
            showings += get_showings_date(cinema_id, cinema)
        return showings
