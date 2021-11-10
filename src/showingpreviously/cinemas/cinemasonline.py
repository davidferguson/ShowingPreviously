import json
from datetime import datetime

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE


CINEMAS_API_URL = 'http://data.cinemas-online.co.uk/cinema/venues'
SHOWINGS_API_URL = 'https://data.cinemas-online.co.uk/cinema/shows?format=now&Venue={cinema_id}'


def get_response(url: str, origin: str) -> requests.Response:
    r = requests.get(url, headers={'origin': origin})
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict(origin: str) -> dict[str, Cinema]:
    r = get_response(CINEMAS_API_URL, origin)
    try:
        cinemas_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {CINEMAS_API_URL}')
    cinemas = {}
    for cinema in cinemas_data:
        cinema_name = cinema['Name']
        cinema_id = cinema['PermaLink']
        cinemas[cinema_id] = Cinema(cinema_name, UK_TIMEZONE)
    return cinemas


def get_attributes(showing: dict[str, any]) -> dict[str, any]:
    attributes = {'format':[]}
    for tag in showing['tags']:
        if tag['is_imax']:
            attributes['format'].append('IMAX')

        if tag['name'] == 'AD':
            attributes['audio-described'] = True
        elif tag['name'] == 'ST':
            attributes['subtitled'] = True
        elif tag['name'] == 'Event':
            attributes['event'] = True
        elif tag['name'] in ['Live', '4K', '70mm', 'Atmos', 'HFR 30', 'IMAX', 'IMAX3D']:
            attributes['format'].append(tag['name'])
        elif tag['name'] == 'Seniors':
            attributes['senior'] = True
        elif tag['name'] == 'Baby':
            attributes['carers-and-babies'] = True

    if len(attributes['format']) == 0:
        del attributes['format']
    return attributes


def get_showings(cinema_id: str, cinema: Cinema, origin: str, chain: Chain) -> [Showing]:
    url = SHOWINGS_API_URL.format(cinema_id=cinema_id)
    r = get_response(url, origin)
    try:
        showings_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {SHOWINGS_API_URL}')

    showings = []
    for film_data in showings_data:
        film_name = film_data['Movie']['Title']
        release_date = film_data['Movie']['ReleaseDate'].replace('Z', '')
        film_year = str(datetime.fromisoformat(release_date).year)
        film = Film(film_name, film_year)
        for showing_date in film_data['ShowDates']:
            for showing in showing_date['Times']:
                date = datetime.fromisoformat(showing['Time'].replace('Z', ''))
                screen = Screen(showing['Screen'])
                json_attributes = {}
                showings.append(Showing(film, date, chain, cinema, screen, json_attributes))
    return showings


class CinemasOnline(ChainArchiver):
    def __init__(self, chain: Chain, origin: str):
        self.chain = chain
        self.origin = origin

    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict(self.origin)
        for cinema_id, cinema in cinemas.items():
            showings += get_showings(cinema_id, cinema, self.origin, self.chain)
        return showings


class ReelCinemas(CinemasOnline):
    def __init__(self):
        super().__init__(Chain('Reel Cinemas'), 'https://reelcinemas.co.uk')
