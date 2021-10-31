import json

from datetime import datetime, timedelta
from typing import Tuple, Iterator
import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing

CINEMAS_URL = 'https://vwc.odeon.co.uk/WSVistaWebClient/ocapi/v1/browsing/master-data/sites'
FILMS_URL = 'https://vwc.odeon.co.uk/WSVistaWebClient/ocapi/v1/browsing/master-data/films'
SHOWINGS_URL = 'https://vwc.odeon.co.uk/WSVistaWebClient/ocapi/v1/browsing/master-data/showtimes/business-date/{date}'

JWT_TOKEN = 'eyJhbGciOiJSUzI1NiIsImtpZCI6IjRBQUQ3MUYwRDI3OURBM0Y2NkMzNjJBM0JGMDRBMDFDNDBBNzU4RjciLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiJxNGJycW1nazQxMWtjOHo5eGJiZzF0YTNueGh5eHJneDIiLCJnaXZlbl9uYW1lIjoiT2Rlb24iLCJmYW1pbHlfbmFtZSI6IldlYiBIb3N0IiwidmlzdGFfb3JnYW5pc2F0aW9uX2NvZGUiOiI4a3Q1ZnZ3MjYzYTR6NjJha2hkcWcyMXBxbTgiLCJyb2xlIjoiQ1hNX0FjY2Vzc1J1bGVzQXBpIiwidG9rZW5fdXNhZ2UiOiJhY2Nlc3NfdG9rZW4iLCJqdGkiOiIwODU1NTZlZi0wM2E4LTRhYWMtYTVkYy03YTNmYTlkNDRhYzMiLCJhdWQiOiJhbGwiLCJhenAiOiJPZGVvbiBXZWJzaXRlIC0gUHJvZHVjdGlvbiIsIm5iZiI6MTYzNTUzNjc1MCwiZXhwIjoxNjM1NTc5OTUwLCJpYXQiOjE2MzU1MzY3NTAsImlzcyI6Imh0dHBzOi8vYXV0aC5tb3ZpZXhjaGFuZ2UuY29tLyJ9.JjPzWagHLBwPbLMIZFwktMBMbAtpEC7Cc3JPbPJUYQzdfUszxMBuIRRshZ4Oqw-f8XIFMmY0c6U2UkW5rhLKTYSS0M16iPT87A6nbCT2sEDNpFtddsAN4eyJR5b68KzydBpK7NhB6mGitjyb0uYJYQyq91fjNpyL1rSQTLZezkY07XYOzqvLvPIQLeRj0a4mbUVVkkeXyGgsuk4s0x2hlvE7e3QQ4NsoXqqINxQlNvJErE5BX-doIwnMeov7WdQyLqs9mPPAigQphkOzvWHjlvp3kXKYXfsSpESu6I9gz5Byg0wmwokL2igCwHOU5zL8q8A8mdqsUWQVDiviikd8p62YQ5zTFNmzWjlCb5zDH4vS9TPyKVb35Mce6HGD7n16X2iN5h5XE8eCwIBtAc-Y5m51ji0SfUnghy44txh1QZ5x_dGH6pDxMjL7-KaOkWBRYdIxrBQB7ySd6EauY8hmiNDx6-rNH9h8GIzos7VyGrD3GQf0g_UzKiEFzvqZ9m-2c996cWLjGz03PTKhYo1f50RiwrNZfHq4DCMwF1cjg6yah0Z_-AaEwIUGMnspwODr8nuISIkxYhOXUhu-DkXqJz9KKjSVNj5_GoclMZo1oFYPZLLaPXpoXGK7Yi7uVarllFkFTYKu1Dlz0QI-_p3ql8GmW6HKhmCGubBMLdBw1T4'
REQUEST_HEADERS = {
    'authorization': f'Bearer {JWT_TOKEN}',
    'accept': 'application/json',
    'user-agent': 'showingpreviously'
}
DAYS_AHEAD = 2
CHAIN = Chain('Odeon')


def get_cinemas_as_dict(cinemas_data: [dict[str, any]]) -> dict[str, Cinema]:
    cinemas = {}
    for cinema in cinemas_data:
        id = cinema['id']
        name = cinema['name']['text']
        # timezone = cinema['ianaTimeZoneName']
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


def get_showings_date(showings_data: any) -> [Showing]:
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
        showings.append(Showing(film, start_time, CHAIN, cinema, screen, json_attributes))
    return showings


def get_api_data() -> Iterator[dict[str, any]]:
    current_date = datetime.now()
    end_date = current_date + timedelta(days=DAYS_AHEAD)
    while current_date < end_date:
        url = SHOWINGS_URL.format(date=current_date.strftime('%Y-%m-%d'))
        r = requests.get(url, headers=REQUEST_HEADERS)
        if r.status_code != 200:
            raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
        try:
            showings_data = r.json()
        except json.JSONDecodeError:
            raise CinemaArchiverException(f'Error decoding JSON data from URL {url}')
        yield showings_data
        current_date += timedelta(days=1)


class Odeon(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        for showings_data in get_api_data():
            showings += get_showings_date(showings_data)
        return showings
