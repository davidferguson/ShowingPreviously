import json
import re

from bs4 import BeautifulSoup
from datetime import datetime, timedelta

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import STANDARD_DAYS_AHEAD, UK_TIMEZONE, UNKNOWN_FILM_YEAR


PICTUREHOUSE_TOKEN_URL = 'https://www.picturehouses.com/'
CINEMAS_API_URL = 'https://www.picturehouses.com/ajax-cinema-list'
SHOWINGS_API_URL = 'https://www.picturehouses.com/api/scheduled-movies-ajax'
FILM_INDEX_URL = 'https://www.picturehouses.com/whats-on'
FILM_DETAILS_URL = 'https://www.picturehouses.com/movie-details/000/{id}/{slug}'

CHAIN = Chain('Picturehouse')

LARAVEL_PATTERN = re.compile(r'laravel_session=(?P<laravel_session>.+?);')
SHOWING_URL_ID_PATTERN = re.compile(r'/movie-details/\d+/(?P<film_id>.+?)/(?P<slug>.+)')
SLUG_YEAR_PATTERN = re.compile(r'(?P<year>(?:18|19|20)\d{2})')
JS_TO_URL_PATTERN = re.compile(r'"(?P<film_link>https?://.+?)"')
DUBBED_LANGUAGE_PATTERN = re.compile(r'Please note, this screening features the Dubbed (?P<dub_language>.+?) version of the film')
SUBBED_LANGUAGE_PATTERN = re.compile(r'have (?P<sub_language>.+?) subtitles')


def get_showing_dates() -> str:
    current_date = datetime.now()
    end_date = current_date + timedelta(days=STANDARD_DAYS_AHEAD)
    while current_date < end_date:
        yield current_date.strftime('%Y-%m-%d')
        current_date += timedelta(days=1)


def get_tokens() -> (str, str):
    r = requests.get(PICTUREHOUSE_TOKEN_URL)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {PICTUREHOUSE_TOKEN_URL}')
    all_cookies = r.headers.get('set-cookie')
    laravel_session = LARAVEL_PATTERN.search(all_cookies).group('laravel_session')
    soup = BeautifulSoup(r.text, features='html.parser')
    token = soup.find('input', {'name': '_token'})['value']
    return laravel_session, token


def get_cinemas(laravel_session: str, token: str) -> dict[str, Cinema]:
    r = requests.post(CINEMAS_API_URL, cookies={'laravel_session': laravel_session}, data={'_token': token})
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {CINEMAS_API_URL}')
    try:
        cinema_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {CINEMAS_API_URL}')
    cinemas = {}
    for cinema in cinema_data['cinema_list']:
        id = cinema['cinema_id']
        name = cinema['name']
        cinemas[id] = Cinema(name, UK_TIMEZONE)
    return cinemas


def get_film_year(film_link: str) -> str:
    # first we inspect the url to see if the date is present in that
    match = SLUG_YEAR_PATTERN.search(film_link)
    if match:
        return match.group('year')

    # then we request the page and look for the date there
    r = requests.get(film_link)
    if r.status_code != 200:
        # sometimes films don't exist for some reason. nothing we can do about that
        return UNKNOWN_FILM_YEAR

    soup = BeautifulSoup(r.text, features='html.parser')
    metadata = soup.find('div', {'class': 'directorDiv'})
    if not metadata:
        return ''
    date = metadata.find('li', text='Release Date :').findNext('li').text
    year = date[-4:]
    return year


def get_film_years(film_year_wants: [str]) -> dict[str, str]:
    r = requests.get(FILM_INDEX_URL)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {FILM_INDEX_URL}')
    soup = BeautifulSoup(r.text, features='html.parser')
    films = {}
    for date in get_showing_dates():
        list_class_name = f'date-{date}'
        for film_list in soup.find_all('li', {'class': list_class_name}):
            for film in film_list.find_all('a', {'class': 'whatson_movie_deatils_url', 'onclick': True}):
                js_value = film['onclick']
                film_link = JS_TO_URL_PATTERN.search(js_value).group('film_link')
                film_id = SHOWING_URL_ID_PATTERN.search(film_link).group('film_id')
                if film_id in films or film_id not in film_year_wants:
                    continue
                year = get_film_year(film_link)
                films[film_id] = year
    return films


def preprocess_film_name(name: str) -> str:
    name_lower = name.lower()
    if name_lower.startswith('toddler time: '):
        return name[14:], {}
    if name_lower.startswith('dog-friendly screening: '):
        return name[24:], {'dog-friendly': True}
    return name, {}


def get_attributes(attributes: [dict[str, any]]) -> dict[str, any]:
    json_attributes = {'format': []}
    for attribute in attributes:
        if attribute['attribute'] == 'ad-trailer':
            json_attributes['ad-trailer-free'] = True
        elif attribute['attribute'] == 'Sub Cinema':
            json_attributes['subtitled'] = True
            language = SUBBED_LANGUAGE_PATTERN.search(attribute['description'])
            if language:
                json_attributes['subtitled'] = language.group('sub_language')
        elif attribute['attribute'] == 'Dub Cinema':
            language = DUBBED_LANGUAGE_PATTERN.search(attribute['description'])
            if language:
                json_attributes['language'] = language.group('dub_language')
        elif attribute['attribute'] == 'LiveSat':
            json_attributes['format'].append('Live')
        elif attribute['attribute'] == 'Audio D':
            json_attributes['audio-described'] = True
        elif attribute['attribute'] == 'HOHSub':
            json_attributes['captioned'] = True
        elif attribute['attribute'] == 'Dolby Atmo':  # note: not a typo - Picturehouse attribute has the 's' missing
            json_attributes['format'].append('Dolby Atmos')
        elif attribute['attribute'] == '4K':
            json_attributes['format'].append('4K')
        elif attribute['attribute'] == 'Toddler Ti':
            json_attributes['carers-and-babies'] = True
        elif attribute['attribute'] == "Kids' Club":
            json_attributes['kids'] = True
    if len(json_attributes['format']) == 0:
        del json_attributes['format']
    return json_attributes


def get_showings(cinemas: [Cinema], laravel_session: str, token: str):
    r = requests.post(SHOWINGS_API_URL, cookies={'laravel_session': laravel_session}, data={'_token': token})
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {SHOWINGS_API_URL}')
    try:
        showings_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {CINEMAS_API_URL}')

    film_year_wants = []
    for movie in showings_data['movies']:
        film_year_wants.append(movie['ScheduledFilmId'])
    film_years = get_film_years(film_year_wants)

    showings = []
    for movie in showings_data['movies']:
        title = movie['Title']
        if movie['ScheduledFilmId'] not in film_years:
            # this is most likely because the film isn't showing in the next STANDARD_DAYS_AHEAD days, so we can skip it
            continue

        title, film_attributes = preprocess_film_name(title)

        year = film_years[movie['ScheduledFilmId']]
        film = Film(title, year)
        for showing in movie['show_times']:
            cinema = cinemas[showing['CinemaId']]
            screen = Screen(showing['ScreenName'])
            time = datetime.fromisoformat(showing['Showtime'])
            showing_attributes = get_attributes(showing['attributes'])
            json_attributes = {**film_attributes, **showing_attributes}
            showing = Showing(film, time, CHAIN, cinema, screen, json_attributes)
            showings.append(showing)
    return showings


class Picturehouse(ChainArchiver):
    def get_showings(self) -> [Showing]:
        laravel_session, token = get_tokens()
        cinemas = get_cinemas(laravel_session, token)
        showings = get_showings(cinemas, laravel_session, token)
        return showings
