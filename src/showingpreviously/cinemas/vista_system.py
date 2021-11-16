import json
import re

from datetime import datetime, timedelta
from typing import Tuple, Iterator
import showingpreviously.requests as requests
from showingpreviously.selenium import get_selenium_webdriver
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import STANDARD_DAYS_AHEAD

CINEMAS_URL = 'https://{api_url}/WSVistaWebClient/ocapi/v1/browsing/master-data/sites'
FILMS_URL = 'https://{api_url}/WSVistaWebClient/ocapi/v1/browsing/master-data/films'
SHOWINGS_URL = 'https://{api_url}/WSVistaWebClient/ocapi/v1/browsing/master-data/showtimes/business-date/{date}'


def get_request_headers(token: str) -> dict[str, str]:
    return {
        'authorization': f'Bearer {token}',
        'accept': 'application/json',
        'user-agent': 'showingpreviously'
    }


def get_cinemas_as_dict(cinemas_data: [dict[str, any]]) -> dict[str, Cinema]:
    cinemas = {}
    for cinema in cinemas_data:
        id = cinema['id']
        name = cinema['name']['text']
        timezone = 'UTC'  # Odeon gives times in UTC already, so there is no need to convert them
        cinemas[id] = Cinema(name, timezone)
    return cinemas


def get_screens_as_dict(screens_data: [dict[str, any]]) -> dict[str, Screen]:
    screens = {}
    for screen in screens_data:
        id = screen['id']
        name = screen['name']['text']
        screens[id] = Screen(name)
    return screens


def get_films_as_dict(films_data: [dict[str, any]]) -> dict[str, Film]:
    films = {}
    for film in films_data:
        id = film['id']
        name = film['title']['text']
        year = str(datetime.fromisoformat(film['releaseDate']).year)
        films[id] = Film(name, year)
    return films


def get_attributes_as_dict(attributes_data: [dict[str, any]]) -> dict[str, Tuple[str, str]]:
    attributes = {}
    for attribute in attributes_data:
        id = attribute['id']
        name: str = attribute['name']['text'].strip()
        if name.lower() == 'audio described':
            attributes[id] = 'audio-described', True
        elif name.lower().endswith(' (audio)'):
            attributes[id] = 'language', name[:-8]
        elif name.lower() == 'open captioned':
            attributes[id] = 'captioned', 'english'
        elif name.lower().startswith('imax'):
            attributes[id] = 'format', 'IMAX'
        elif name.lower().startswith('isense'):
            attributes[id] = 'format', 'iSense'
        elif name.lower().startswith('dolby'):
            attributes[id] = 'format', 'Dolby Cinema'
        elif name.lower().startswith('4k'):
            attributes[id] = 'format', '4K'
    return attributes


def get_showing_attributes(showing_attributes: [str], attributes: dict[str, Tuple[str, str]]) -> dict[str, any]:
    json_attributes = {}
    for attribute_id in showing_attributes:
        if attribute_id in attributes:
            key, value = attributes[attribute_id]
            if key in ['format']:
                if key not in json_attributes:
                    json_attributes[key] = []
                json_attributes[key].append(value)
            else:
                json_attributes[key] = value
    return json_attributes


def get_showings_date(showings_data: any, chain_name: str) -> [Showing]:
    showings = []
    showtimes = showings_data['showtimes']

    cinemas = get_cinemas_as_dict(showings_data['relatedData']['sites'])
    screens = get_screens_as_dict(showings_data['relatedData']['screens'])
    films = get_films_as_dict(showings_data['relatedData']['films'])
    attributes = get_attributes_as_dict(showings_data['relatedData']['attributes'])

    for show in showtimes:
        cinema = cinemas[show['siteId']]
        screen = screens[show['screenId']]
        film = films[show['filmId']]
        start_time = datetime.fromisoformat(show['schedule']['startsAt']).replace(tzinfo=None)
        json_attributes = get_showing_attributes(show['attributeIds'], attributes)
        showings.append(Showing(film, start_time, Chain(chain_name), cinema, screen, json_attributes))
    return showings


def get_api_data(api_url: str, token: str) -> Iterator[dict[str, any]]:
    request_headers = get_request_headers(token)
    current_date = datetime.now()
    end_date = current_date + timedelta(days=STANDARD_DAYS_AHEAD)
    while current_date < end_date:
        url = SHOWINGS_URL.format(api_url=api_url, date=current_date.strftime('%Y-%m-%d'))
        r = requests.get(url, headers=request_headers)
        if r.status_code != 200:
            raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
        try:
            showings_data = r.json()
        except json.JSONDecodeError:
            raise CinemaArchiverException(f'Error decoding JSON data from URL {url}')
        yield showings_data
        current_date += timedelta(days=1)


class VistaSystem(ChainArchiver):
    def __init__(self, api_url: str, chain_name: str,):
        super().__init__()
        self.chain_name = chain_name
        self.api_url = api_url

    def get_showings(self) -> [Showing]:
        token = self.get_token()
        showings = []
        for showings_data in get_api_data(self.api_url, token):
            showings += get_showings_date(showings_data, self.chain_name)
        return showings

    def get_token(self) -> str:
        pass


# Odeon variant
class Odeon(VistaSystem):
    def __init__(self):
        super().__init__('vwc.odeon.co.uk', 'Odeon')

    def get_token(self) -> str:
        driver = get_selenium_webdriver()
        driver.get('https://www.odeon.co.uk/')
        jwt_finder = re.compile(r'"authToken":"(?P<jwt_token>.+?)"')
        token = jwt_finder.search(driver.page_source).group('jwt_token')
        return token


# Curzon variant
class Curzon(VistaSystem):
    def __init__(self):
        super().__init__('vwc.curzon.com', 'Curzon')

    def get_token(self) -> str:
        r = requests.get('https://www.curzon.com', headers={'user-agent': 'showingpreviously'})
        jwt_finder = re.compile(r'"authToken":"(?P<jwt_token>.+?)"')
        token = jwt_finder.search(r.text).group('jwt_token')
        return token
