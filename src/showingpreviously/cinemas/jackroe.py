import re

from datetime import datetime, timedelta
from bs4 import BeautifulSoup

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import STANDARD_DAYS_AHEAD, UK_TIMEZONE, UNKNOWN_FILM_YEAR


SHOWING_LIST_URL = 'https://www.jack-roe.co.uk/websales/sales/{cinema_code}/start?comingsoon=1'
SHOWING_URL = 'https://www.jack-roe.co.uk/websales/sales/{cinema_code}/actual_book?perfcode={showing_code}'
SHOWING_CODE_PATTERN = re.compile(r'book\?perfcode=(?P<showing_code>\d+)$')
SHOWING_INFO_PATTERN = re.compile(r'at(?P<time>\s+\d+:\d+)\s+on\s+(?P<date>.+?)\s+showing in\s+(?P<screen_name>.+?)\s*<')
FINISHED_TEXT = 'We are afraid that sales for the following performance have now finished'

MOVIEHOUSE_BASE_URL = 'https://www.moviehouse.co.uk'
MOVIEHOUSE_CINEMAS_URL = f'{MOVIEHOUSE_BASE_URL}/Home/AllCinemas'
MOVIEHOUSE_CHAIN = Chain('Movie House Cinemas')
MOVIEHOUSE_LOCATION_CODE_PATTERN = re.compile(r'var\s+location\s*=\s*"(?P<location_code>.+?)";')

SCOTTCINEMAS_BASE_URL = 'https://www.scottcinemas.co.uk'
SCOTTCINEMAS_CHAIN = Chain('Scott Cinemas')
SCOTTCINEMAS_LOCATION_CODE_PATTERN = re.compile(r'/websales/sales/(?P<location_code>.+?)/actual_book')

WTWCINEMAS_BASE_URL = 'https://wtwcinemas.co.uk'
WTWCINEMAS_CHAIN = Chain('WTW Cinemas')
WTWCINEMAS_LOCATION_CODE_PATTERN = re.compile(r'/websales/sales/(?P<location_code>.+?)/book')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_attributes(html: str) -> dict[str, any]:
    attributes = {}
    if 'Audio Description' in html:
        attributes['audio-described'] = True
    if 'Subtitled' in html:
        attributes['subtitled'] = True
    return attributes


def get_showings_date(cinema_id: str, cinema: Cinema, chain: Chain, showing_dates: [str]) -> [Showing]:
    url = SHOWING_LIST_URL.format(cinema_code=cinema_id)
    r = get_response(url)
    soup = BeautifulSoup(r.text, features='html.parser')
    showings = []
    for movie_row in soup.find_all('div', {'class': 'start-performance-box'}):
        film_title = movie_row.find('h3').text.strip()
        film = Film(film_title, UNKNOWN_FILM_YEAR)
        for day_row in movie_row.find_all('div', {'class': 'col-md-4'}):
            day = day_row.text.strip()
            if day not in showing_dates:
                continue
            booking_btn_row = day_row.find_next('div', {'class': 'col-md-8'})
            for booking_btn in booking_btn_row.find_all('a', {'class': 'btn'}):
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
                date = showing_info.group('date').strip()
                time = showing_info.group('time').strip()
                date_and_time = datetime.strptime(f'{date} {time}', '%A %d %B %Y %H:%M')
                json_attributes = get_attributes(r.text)
                showings.append(Showing(film, date_and_time, chain, cinema, screen, json_attributes))
    return showings


def get_showing_dates() -> [str]:
    showing_dates = []
    current_date = datetime.now()
    end_date = current_date + timedelta(days=STANDARD_DAYS_AHEAD)
    while current_date < end_date:
        showing_dates.append(current_date.strftime('%A %-d %B'))
        current_date += timedelta(days=1)
    return showing_dates


class JackRoe(ChainArchiver):
    def __init__(self, chain: Chain):
        self.chain = chain

    def get_cinemas(self) -> dict[str, Cinema]:
        return {}

    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = self.get_cinemas()
        showing_dates = get_showing_dates()
        for cinema_id, cinema in cinemas.items():
            showings += get_showings_date(cinema_id, cinema, self.chain, showing_dates)
        return showings


class MovieHouse(JackRoe):
    def __init__(self):
        super().__init__(MOVIEHOUSE_CHAIN)

    def get_cinemas(self) -> dict[str, Cinema]:
        r = get_response(MOVIEHOUSE_CINEMAS_URL)
        soup = BeautifulSoup(r.text, features='html.parser')
        container = soup.find('div', {'class': 'col-sm-push-1'})
        cinemas = {}
        for cinema_link in container.find_all('a', {'href': True}):
            cinema_name = cinema_link.text.replace('MOVIE HOUSE', '').strip()
            cinema_link = MOVIEHOUSE_BASE_URL + cinema_link['href']
            r = get_response(cinema_link)
            cinema_id = MOVIEHOUSE_LOCATION_CODE_PATTERN.search(r.text).group('location_code')
            cinemas[cinema_id] = Cinema(cinema_name, UK_TIMEZONE)
        return cinemas


class ScottCinemas(JackRoe):
    def __init__(self):
        super().__init__(SCOTTCINEMAS_CHAIN)

    def get_cinemas(self) -> dict[str, Cinema]:
        r = get_response(SCOTTCINEMAS_BASE_URL)
        soup = BeautifulSoup(r.text, features='html.parser')
        select = soup.find('select', {'name': 'cinema_location'})
        scott_cinemas = select.find('optgroup', {'label': 'Scott Cinemas'})
        cinemas = {}
        for cinema_option in scott_cinemas.find_all('option', {'value': True}):
            cinema_name = cinema_option.text.strip()
            cinema_id = cinema_option['value']
            cinema_link = f'{SCOTTCINEMAS_BASE_URL}/switchto/{cinema_id}'
            r = get_response(cinema_link)
            cinema_url = r.url
            soup = BeautifulSoup(r.text, features='html.parser')
            booking_link = cinema_url + soup.find('a', href=lambda href: href and '/book-now/' in href)['href']
            r = get_response(booking_link)
            cinema_id = SCOTTCINEMAS_LOCATION_CODE_PATTERN.search(r.text).group('location_code')
            cinemas[cinema_id] = Cinema(cinema_name, UK_TIMEZONE)
        return cinemas


class WTWCinemas(JackRoe):
    def __init__(self):
        super().__init__(WTWCINEMAS_CHAIN)

    def get_cinemas(self) -> dict[str, Cinema]:
        r = get_response(WTWCINEMAS_BASE_URL)
        soup = BeautifulSoup(r.text, features='html.parser')
        list = soup.find('ul', {'class': 'listing--items'})
        cinemas = {}
        for a in list.find_all('a', {'data-location': True}):
            cinema_name = a.text.replace('\n', ' - ').strip()
            location_code = a['data-location']
            cinema_link = f'{WTWCINEMAS_BASE_URL}/{location_code}/whats-on/'
            r = get_response(cinema_link)
            soup = BeautifulSoup(r.text, features='html.parser')
            booking_link = soup.find('a', href=lambda href: href and '/book' in href)['href']
            r = get_response(booking_link)
            cinema_id = WTWCINEMAS_LOCATION_CODE_PATTERN.search(r.text).group('location_code')
            cinemas[cinema_id] = Cinema(cinema_name, UK_TIMEZONE)
        return cinemas
