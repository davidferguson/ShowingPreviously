import re
import json
from datetime import datetime
from typing import Optional

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing


CINEMAS_URL = 'https://walsall.thelight.co.uk'
SHOWINGS_URL = '{cinema_url}/resource/services/miniguide/data.ashx'
SCREEN_API_URL = '{cinema_url}/api/book/cinema/session'

DAYS_AHEAD = 2
TOKEN_PATTERN = re.compile(r'\'Token\':\s*\'(?P<token>.+?)\'')
CINEMAS_JSON_PATTERN = re.compile(r'var\s+__sites\s*=\s*(?P<cinemas_json>.+?)\s*;')
SHOWINGS_JSON_PATTERN = re.compile(r'var\s+__gfminiguidedata\s*=\s*(?P<showings_json>.+?)\s*;')
SCREEN_LIGHTCINEMAS_PATTERN = re.compile(r'cinema-screen-name">.+?-\s*(?P<screen_name>.+?)<')
CHAIN = Chain('The Light Cinemas')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_token(cinema_url: str) -> str:
    r = requests.get(cinema_url)
    token = TOKEN_PATTERN.search(r.text).group('token')
    return token


def get_lpvs(cinema_url: str) -> str:
    r = requests.get(cinema_url)
    lpvs = r.cookies.get('lpvs')
    return lpvs


def get_cinemas_as_dict() -> dict[str, Cinema]:
    r = get_response(CINEMAS_URL)
    cinemas_json = CINEMAS_JSON_PATTERN.search(r.text).group('cinemas_json')
    try:
        cinemas_data = json.loads(cinemas_json)
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from string: {cinemas_json}')
    cinemas = {}
    for cinema in cinemas_data:
        cinema_name = cinema['title']
        cinema_url = cinema['url']
        cinemas[cinema_url] = Cinema(cinema_name, 'Europe/London')
    return cinemas


def get_attributes(collections: [dict[str, any]]) -> dict[str, any]:
    attributes = {}
    for collection in collections:
        if collection['Title'] == 'Audio Description':
            attributes['audio-described'] = True
        elif collection['Title'] == 'Subtitled for hard of hearing':
            attributes['captioned'] = True
        elif collection['Title'] == 'Silver Screen':
            attributes['senior'] = True
        elif collection['Title'] == 'Baby-friendly':
            attributes['carers-and-babies'] = True
    return attributes


def get_screen_thelight(cinema_url: str, showing_id: str, token: str) -> Screen:
    url = SCREEN_API_URL.format(cinema_url=cinema_url)
    data = {'SessionId': showing_id, 'Token': token}
    r = requests.post(url, data=json.dumps(data))
    try:
        booking_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL: {url}')
    screen_name = booking_data['Data']['ScreenName']
    return Screen(screen_name)


def get_screen_lightcinemas(booking_url: str, lpvs: str):
    r = requests.get(booking_url, cookies={'lpvs': lpvs})
    screen_name = SCREEN_LIGHTCINEMAS_PATTERN.search(r.text).group('screen_name')
    return Screen(screen_name)


def process_showing(showing, date: str, cinema_url: str, cinema: Cinema, film: Film, token: str, lpvs: str) -> Optional[Showing]:
    if 'BOID' not in showing:
        # this means the screening has already started, or can't be booked, so we skip it
        return None
    showing_id = showing['BOID']
    time = showing['Display']
    date_and_time = datetime.strptime(f'{date} {time}', '%Y%m%d %H.%M')
    json_attributes = get_attributes(showing['Collections'])
    if 'Url' in showing and showing['Url'].strip() != '':
        screen = get_screen_lightcinemas(showing['Url'], lpvs)
    else:
        screen = get_screen_thelight(cinema_url, showing_id, token)
    return Showing(film, date_and_time, CHAIN, cinema, screen, json_attributes)


def get_showings(cinema_url: str, cinema: Cinema) -> [Showing]:
    token = lpvs = None
    if 'thelight' in cinema_url:
        token = get_token(cinema_url)
    else:
        lpvs = get_lpvs(cinema_url)
    url = SHOWINGS_URL.format(cinema_url=cinema_url)
    r = get_response(url)
    showings_json = SHOWINGS_JSON_PATTERN.search(r.text).group('showings_json')
    try:
        showings_data = json.loads(showings_json)
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from string: {showings_json}')
    showings = []
    for film_data in showings_data['Schedule']:
        film_name = film_data['Title']
        film_year = '0'  # todo: somehow get the year
        film = Film(film_name, film_year)
        for i in range(0, min(DAYS_AHEAD, len(film_data['Dates']))):
            day = film_data['Dates'][i]
            date = day['Key']
            if 'Sessions' not in day:
                for format in day['Formats']:
                    for showing in format['Sessions']:
                        res = process_showing(showing, date, cinema_url, cinema, film, token, lpvs)
                        if res is not None:
                            showings.append(res)
            else:
                for showing in day['Sessions']:
                    res = process_showing(showing, date, cinema_url, cinema, film, token, lpvs)
                    if res is not None:
                        showings.append(res)
    return showings


class TheLight(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_url, cinema in cinemas.items():
            showings += get_showings(cinema_url, cinema)
        return showings
