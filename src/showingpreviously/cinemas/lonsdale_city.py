import datetime
import json

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE


FILM_LISTINGS_API = 'https://data.cinemas-online.co.uk/cinema/shows?format=now&Venue=annan'
BASE_URL = 'https://lonsdalecitycinemas.co.uk'
FILM_NAME_IGNORES = []

CHAIN = Chain('Lonsdale City')
CINEMA = Cinema('Lonsdale City', UK_TIMEZONE)


def get_response(url: str) -> requests.Response:
    r = requests.get(url, headers={'Origin': BASE_URL})
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


class LonsdaleCity(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        resp = get_response(FILM_LISTINGS_API)
        api_data = json.loads(resp.text)
        for showing_film in api_data:
            film_attributes = {}
            film_name = showing_film['Movie']['Title']
            film_year = str(datetime.datetime.strptime(showing_film['Movie']['ReleaseDate'], '%Y-%m-%dT%H:%M:%S.000Z').year)
            film = Film(film_name, film_year)
            try:
                if showing_film['Movie']['EventCinema']:
                    film_attributes['event'] = True
            except KeyError:
                pass
            for showing_date in showing_film['ShowDates']:
                for showing_event in showing_date['Times']:
                    showing_time_str = showing_event['Time']
                    showing_time = datetime.datetime.strptime(showing_time_str, '%Y-%m-%dT%H:%M:%S.000Z')
                    showing_screen = Screen(showing_event['Screen'])
                    showing = Showing(
                        film=film,
                        time=showing_time,
                        chain=CHAIN,
                        cinema=CINEMA,
                        screen=showing_screen,
                        json_attributes=film_attributes
                    )
                    showings.append(showing)
        return showings
