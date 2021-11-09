import re
import sys

from datetime import datetime, timedelta
from bs4 import BeautifulSoup

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import STANDARD_DAYS_AHEAD, UK_TIMEZONE, UNKNOWN_FILM_YEAR


BASE_URL = 'https://www.moviehouse.co.uk'
CINEMAS_URL = f'{BASE_URL}/Home/AllCinemas'
SHOWING_LIST_URL = f'{BASE_URL}/Movie/LoadShowTimesPartial'
SHOWING_URL = 'https://www.jack-roe.co.uk/websales/sales/{cinema_code}/actual_book?perfcode={showing_code}'
LOCATION_CODE_PATTERN = re.compile(r'var\s+location\s*=\s*"(?P<location_code>.+?)";')
SHOWING_CODE_PATTERN = re.compile(r'/(?P<showing_code>\d+)$')
SHOWING_INFO_PATTERN = re.compile(r'at(?P<time>\s+\d+:\d+)\s+on\s+(?P<date>.+?)\s+showing in\s+(?P<screen_name>.+?)\s*<')
FINISHED_TEXT = 'We are afraid that sales for the following performance have now finished'

CHAIN = Chain('Movie House Cinemas')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict() -> dict[str, Cinema]:
    r = get_response(CINEMAS_URL)
    soup = BeautifulSoup(r.text, features='html.parser')
    container = soup.find('div', {'class': 'col-sm-push-1'})
    cinemas = {}
    for cinema_link in container.find_all('a', {'href': True}):
        cinema_name = cinema_link.text.replace('MOVIE HOUSE', '').strip()
        cinema_link = BASE_URL + cinema_link['href']
        r = get_response(cinema_link)
        cinema_id = LOCATION_CODE_PATTERN.search(r.text).group('location_code')
        cinemas[cinema_id] = Cinema(cinema_name, UK_TIMEZONE)
    return cinemas


def get_showings_date(cinema_id: str, cinema: Cinema, date: str) -> [Showing]:
    data = {
        'Date': date,
        'Location': cinema_id
    }
    r = requests.post(SHOWING_LIST_URL, data=data)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {SHOWING_LIST_URL}')
    soup = BeautifulSoup(r.text, features='html.parser')
    showings = []
    for movie_row in soup.find_all('section'):
        try:
            film_title = movie_row.find('h2', {'class': 'block__title'}).text
        except:
            print(movie_row)
            sys.exit(0)
        film = Film(film_title, UNKNOWN_FILM_YEAR)
        for booking_btn in movie_row.find_all('a', {'class': 'btn'}):
            booking_link = booking_btn['href']
            showing_code = SHOWING_CODE_PATTERN.search(booking_link).group('showing_code')
            url = SHOWING_URL.format(cinema_code=cinema_id, showing_code=showing_code)
            r = get_response(url)
            if FINISHED_TEXT in r.text:
                # the screening has already happened, and we can't get the screen any more
                # skip it
                continue
            showing_info = SHOWING_INFO_PATTERN.search(r.text)
            screen = Screen(showing_info.group('screen_name').replace('  ', ' '))
            time = showing_info.group('time').strip()
            date_and_time = datetime.fromisoformat(f'{date} {time}')
            showings.append(Showing(film, date_and_time, CHAIN, cinema, screen, {}))
    return showings


def get_showing_dates() -> str:
    current_date = datetime.now()
    end_date = current_date + timedelta(days=STANDARD_DAYS_AHEAD)
    while current_date < end_date:
        yield current_date.strftime('%Y-%m-%d')
        current_date += timedelta(days=1)


class MovieHouse(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_id, cinema in cinemas.items():
            for date in get_showing_dates():
                showings += get_showings_date(cinema_id, cinema, date)
        return showings
