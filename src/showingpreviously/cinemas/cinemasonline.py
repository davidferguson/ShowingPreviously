import json
from datetime import datetime
from bs4 import BeautifulSoup

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE


CINEMAS_API_URL = 'http://data.cinemas-online.co.uk/cinema/venues'
SHOWINGS_API_URL = 'https://data.cinemas-online.co.uk/cinema/shows?format=now&Venue={cinema_id}'


def get_response(url: str, origin: str) -> requests.Response:
    r = requests.get(url, headers={'origin': origin})
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url} with origin {origin}')
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
    def __init__(self, chain: Chain, origins: [str]):
        self.chain = chain
        self.origins = origins

    def get_showings(self) -> [Showing]:
        showings = []
        for origin in self.origins:
            cinemas = get_cinemas_as_dict(origin)
            for cinema_id, cinema in cinemas.items():
                showings += get_showings(cinema_id, cinema, origin, self.chain)
        return showings


class ReelCinemas(CinemasOnline):
    def __init__(self):
        super().__init__(Chain('Reel Cinemas'), ['https://reelcinemas.co.uk'])


class NorthernMorris(CinemasOnline):
    def __init__(self):
        cinema_origins = self.get_origins()
        super().__init__(Chain('Northern Morris Cinemas'), cinema_origins)

    def get_origins(self):
        r = get_response('https://nm-cinemas.co.uk/', '')
        soup = BeautifulSoup(r.text, features='html.parser')
        cinema_origins = []
        for cinema_block in soup.find_all('div', {'class': 'venue-container'}):
            link = cinema_block.find('a', {'href': True})['href']
            link = link.replace('http:', 'https:').replace('.co.uk/', '.co.uk')
            cinema_origins.append(link)
        return cinema_origins
