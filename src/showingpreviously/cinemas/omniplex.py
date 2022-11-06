from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import STANDARD_DAYS_AHEAD, UK_TIMEZONE, UNKNOWN_FILM_YEAR, UNKNOWN_SCREEN


CINEMAS_URL = 'https://www.omniplex.ie/'
SHOWINGS_URL = 'https://www.omniplex.ie/cinema/{cinema_id}'
SCREEN_NAME_PATTERN = re.compile(r'var\s+screen\s*=\s*\'(?P<screen_name>.+?)\';')

CHAIN = Chain('Omniplex Cinemas')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict() -> dict[str, Cinema]:
    r = get_response(CINEMAS_URL)
    soup = BeautifulSoup(r.text, features='html.parser')
    cinema_select = soup.find('select', {'id': 'homeSelectCinema'})
    cinemas = {}
    for cinema_option in cinema_select.find_all('option', {'id': True, 'data-thissite': True}):
        cinema_name = cinema_option.text.strip()
        cinema_id = cinema_option['id']
        cinemas[cinema_id] = Cinema(cinema_name, UK_TIMEZONE)
    return cinemas


def get_attributes(at: str) -> dict[str, any]:
    at = at.lower()
    attributes = {'format': []}
    if 'subtitled' in at:
        attributes['subtitled'] = True
    if 'sensory' in at:
        attributes['format'].append('sensory')
    if len(attributes['format']) == 0:
        del attributes['format']
    return attributes


def get_showing_screen(booking_link: str) -> Screen:
    r = get_response(booking_link)
    if 'Booking Error' in r.text:
        return UNKNOWN_SCREEN
    screen_name = SCREEN_NAME_PATTERN.search(r.text).group('screen_name')
    screen = Screen(screen_name)
    return screen


def get_showings_date(cinema_id: str, cinema: Cinema, dates: [str]) -> [Showing]:
    url = SHOWINGS_URL.format(cinema_id=cinema_id)
    r = get_response(url)
    soup = BeautifulSoup(r.text, features='html.parser')
    showings = []
    for cinema_block in soup.find_all('div', {'class': 'rightHolder'}):
        film_title = cinema_block.find('h3').text
        film = Film(film_title, UNKNOWN_FILM_YEAR)
        for date in dates:
            showing_block = cinema_block.find('div', {'class': 'OMP_listingDate', 'data-date': date})
            if showing_block is None:
                continue
            for show_type in showing_block.find_all('div', {'class': 'OMP_perfList'}):
                for showing_btn in show_type.find_all('a', {'class': 'OMP_buttonSelection', 'href': True}):
                    booking_link = showing_btn['href']
                    time = showing_btn.find('strong').text
                    date_and_time = datetime.strptime(f'{date} {time}', '%d-%m-%Y %H:%M')
                    screen = get_showing_screen(booking_link)
                    json_attributes = get_attributes(showing_btn['data-at'])
                    showings.append(Showing(film, date_and_time, CHAIN, cinema, screen, json_attributes))
    return showings


def get_showing_dates() -> [str]:
    current_date = datetime.now()
    end_date = current_date + timedelta(days=STANDARD_DAYS_AHEAD)
    dates = []
    while current_date < end_date:
        dates.append(current_date.strftime('%d-%m-%Y'))
        current_date += timedelta(days=1)
    return dates


class Omniplex(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        dates = get_showing_dates()
        for cinema_id, cinema in cinemas.items():
            showings += get_showings_date(cinema_id, cinema, dates)
        return showings
