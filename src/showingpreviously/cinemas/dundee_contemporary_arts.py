import json
import re

from typing import Iterator, Tuple
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import STANDARD_DAYS_AHEAD, UK_TIMEZONE


FILM_INDEX_URL = 'https://www.dca.org.uk/whats-on/films?from={start}&to={end}'
EVENT_API_URL = 'https://www.dca.org.uk/api/event-instances/{id}'
SCREEN_URL = 'https://tickets.dca.org.uk/dundeeca/website/ChooseSeats.aspx?EventInstanceId={showing_id}'

CHAIN = Chain('Dundee Contemporary Arts')
CINEMA = Cinema('Dundee Contemporary Arts', UK_TIMEZONE)

SUBTITLE_PATTERN = re.compile(r'(?P<language>.+?) with (?P<subtitle>.+?) subtitles')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_film_index_url() -> str:
    start_date = datetime.now()
    end_date = start_date + timedelta(days=STANDARD_DAYS_AHEAD)
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    return FILM_INDEX_URL.format(start=start_str, end=end_str)


def get_film_links_from_index(index_url: str) -> Iterator[str]:
    r = get_response(index_url)
    soup = BeautifulSoup(r.text, features='html.parser')
    main_content = soup.find('div', {'id': 'content-main'})
    if not main_content:
        raise CinemaArchiverException(f'Could not get main content of URL {index_url}')
    for film_item in main_content.find_all('div', {'class': 'article event'}):
        film_title = film_item.find('h2')
        link_location = film_title.find('a', href=True)['href']
        location = film_item.find('p', {'class': 'location'}).text
        if location.strip().lower() != 'cinema':
            continue
        yield link_location


def get_film_info_from_url(film_url: str) -> (str, str, str, dict[str, any]):
    r = get_response(film_url)
    soup = BeautifulSoup(r.text, features='html.parser')
    name = soup.find('h1').text
    metadata = soup.find('dl', {'class': 'metadata'})
    year = metadata.find('dt', text='Year').findNext('dd').text
    event_id = soup.find('div', {'class': 'times full'})['data-event']
    attributes = {}

    if name.lower().strip().startswith('senior citizen kane:'):
        name = name[20:].strip()
        attributes['senior'] = True

    # if the film is in another language
    language_dt = metadata.find('dt', text='Language')
    if language_dt is not None:
        language = language_dt.findNext('dd').text
        attributes['language'] = language
        # if there is a subtitle for this film
        match = SUBTITLE_PATTERN.match(language)
        if match:
            attributes['language'] = match.group('language')
            attributes['subtitled'] = match.group('subtitle')

    # if the film format is specified
    format_dt = metadata.find('dt', text='Format')
    if format_dt is not None:
        format = format_dt.findNext('dd').text
        attributes['format'] = format

    return name, year, event_id, attributes


def get_screen(showing_id: int) -> Screen:
    url = SCREEN_URL.format(showing_id=showing_id)
    r = get_response(url)
    soup = BeautifulSoup(r.text, features='html.parser')
    screen_name = soup.find('span', {'class': 'AreaName'}).text
    return Screen(screen_name)


def get_event_showings(event_id: str) -> Iterator[Tuple[datetime, dict[str, any]]]:
    api_url = EVENT_API_URL.format(id=event_id)
    r = get_response(api_url)
    try:
        event_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {api_url}')
    if 'instances' not in event_data:
        raise CinemaArchiverException('JSON data does not have instances key')
    for instance in event_data['instances']:
        if 'ymd' not in instance or 'time' not in instance:
            raise CinemaArchiverException('Missing attribute ymd or time in JSON')
        year = instance['ymd'][0]
        month = instance['ymd'][1]
        day = instance['ymd'][2]
        time = instance['time']
        timestamp_string = f'{year}-{month}-{day} {time}'
        format_string = '%Y-%m-%d %H:%M'
        try:
            timestamp = datetime.strptime(timestamp_string, format_string)
        except ValueError:
            raise CinemaArchiverException(f'Error parsing timestamp "{timestamp_string}" with format "{format_string}"')

        screen = get_screen(instance['id'])

        json_attributes = {}

        if 'captioned' in instance and instance['captioned'] == 'Yes':
            json_attributes['captioned'] = 'english'

        yield timestamp, screen, json_attributes


class DundeeContemporaryArts(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        index_url = get_film_index_url()
        for film_link in get_film_links_from_index(index_url):
            name, year, event_id, film_attributes = get_film_info_from_url(film_link)
            film = Film(name, year)
            for timestamp, screen, showing_attributes in get_event_showings(event_id):
                json_attributes = {**film_attributes, **showing_attributes}
                showing = Showing(film, timestamp, CHAIN, CINEMA, screen, json_attributes)
                showings.append(showing)
        return showings
