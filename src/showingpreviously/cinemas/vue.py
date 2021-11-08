import json

from datetime import datetime, timedelta
import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import STANDARD_DAYS_AHEAD, UK_TIMEZONE


CINEMAS_API_URL = 'https://www.myvue.com/data/locations/'
SHOWINGS_API_URL = 'https://www.myvue.com/data/filmswithshowings/{cinema_id}?requestedDate={date}'

CHAIN = Chain('VUE UK')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict() -> dict[str, Cinema]:
    r = get_response(CINEMAS_API_URL)
    try:
        cinemas_data = r.json()
    except json.JSONDecodeError:
        raise CinemaArchiverException(f'Error decoding JSON data from URL {CINEMAS_API_URL}')
    cinemas = {}
    for alphabetical in cinemas_data['venues']:
        for cinema in alphabetical['cinemas']:
            id = cinema['id']
            name = cinema['name']
            timezone = UK_TIMEZONE
            cinemas[id] = Cinema(name, timezone)
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


def get_showings_date(cinema_id: str, cinema: Cinema, date: str) -> [Showing]:
    url = SHOWINGS_API_URL.format(cinema_id=cinema_id, date=date)
    r = get_response(url)
    try:
        showings_data = r.json()
    except json.JSONDecodeError:
        # raise CinemaArchiverException(f'Error decoding JSON data from URL {url}')
        # VUE has an API bug where sometimes this sometimes gives a redirect, not JSON.
        # best way of dealing with this is to skip the day
        return []

    showings = []
    for film_data in showings_data['films']:
        film_name = film_data['title']
        film_year = film_data['info_release'][-4:]
        film = Film(film_name, film_year)
        for showing_day in film_data['showings']:
            date = showing_day['date_time']
            for showing in showing_day['times']:
                screen = Screen(showing['screen_name'])
                time = showing['time']
                date_and_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %I:%M %p')
                json_attributes = get_attributes(showing)
                showings.append(Showing(film, date_and_time, CHAIN, cinema, screen, json_attributes))
    return showings


def get_showing_dates() -> str:
    current_date = datetime.now()
    end_date = current_date + timedelta(days=STANDARD_DAYS_AHEAD)
    while current_date < end_date:
        yield current_date.strftime('%Y-%m-%d')
        current_date += timedelta(days=1)


class Vue(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_id, cinema in cinemas.items():
            for date in get_showing_dates():
                showings += get_showings_date(cinema_id, cinema, date)
        return showings
