import time
import re
from datetime import datetime
from bs4 import BeautifulSoup

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE
from showingpreviously.cinemas.lpvs import get_showings as lpvs_get_showings


SHOWING_LIST_URL = '{cinema_url}/?when={date_code}&type=all'
SCREEN_NAME_PATTERN = re.compile(r'Showing In&nbsp;(?P<screen_name>.+?) -')
SCREENING_FINISHED_TEXT = 'The performance has expired, or been taken off sale'
SCREENING_NO_EVENTS_TEXT = 'No event exists for the specified event code.'


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas_as_dict() -> dict[str, Cinema]:
    form_data = {}
    r = get_response(Parkway.CINEMAS_URL)
    soup = BeautifulSoup(r.text, features='html.parser')
    form_data['__VIEWSTATE'] = soup.find('input', {'name': '__VIEWSTATE'})['value']
    form_data['__VIEWSTATEGENERATOR'] = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
    cinemas_list = soup.find('ul', {'class': 'cinemas'})
    cinemas = {}
    for cinema_item in cinemas_list.find_all('li'):
        cinema_name = next(cinema_item.find('strong').children)
        form_data['go'] = cinema_item.find('button', {'value': True})['value']
        r = requests.post(Parkway.CINEMAS_URL, data=form_data)
        cinema_url = r.url
        cinemas[cinema_url] = Cinema(cinema_name, UK_TIMEZONE)
    return cinemas


def get_date_and_screen(booking_url: str, delay_time: int) -> (datetime, Screen):
    try:
        r = get_response(booking_url)
    except requests.exceptions.ConnectionError:
        # admit-one.eu has annoying rate limiting. try again, with an increased back-off
        delay_time += 10
        time.sleep(delay_time)
        return get_date_and_screen(booking_url, delay_time)
    if SCREENING_FINISHED_TEXT in r.text or SCREENING_NO_EVENTS_TEXT in r.text:
        # the screening has ended, and we can't get the screen name. return nothing
        return None, None
    soup = BeautifulSoup(r.text, features='html.parser')
    date_str = next(soup.find('div', {'class': 'OLCT_ticketInfoText'}).children).text.strip()
    date = datetime.strptime(date_str, '%A %d %B %Y @ %H:%M')
    screen_name = SCREEN_NAME_PATTERN.search(r.text).group('screen_name')
    return date, Screen(screen_name)


def get_film(film_url: str, title: str) -> Film:
    r = get_response(film_url)
    soup = BeautifulSoup(r.text, features='html.parser')
    release_date = soup.find('b', text='Release Date:').next_sibling.text.strip()
    release_year = release_date[-4:]
    return Film(title, release_year)


def get_showings(cinema_url: str, cinema: Cinema) -> [Showing]:
    showings = []
    for date_code in ['today', 'tomorrow', 'plus2']:
        url = SHOWING_LIST_URL.format(cinema_url=cinema_url, date_code=date_code)
        r = get_response(url)
        soup = BeautifulSoup(r.text, features='html.parser')
        for film_card in soup.find_all('div', {'class': 'OLCT_performance'}):
            film_h3 = film_card.find('h3')
            film_title = film_h3.text
            film_link = film_h3.find_parent('a', {'href': True})['href']
            film = get_film(film_link, film_title)

            for booking_link in film_card.find_all('a', href=lambda href: href and 'admit-one.eu/?p=tickets' in href):
                link = booking_link['href']
                date, screen = get_date_and_screen(link, 0)
                if date is None or screen is None:
                    # the screening has expired, we can't do anything with it
                    continue
                showings.append(Showing(film, date, Parkway.CHAIN, cinema, screen, {}))
    return showings


class Parkway(ChainArchiver):
    CHAIN = Chain('Parkway Cinemas')
    CINEMAS_URL = 'https://www.parkwaycinemas.co.uk/'

    # this method either uses the lpvs code, or the admit-one code
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas_as_dict()
        for cinema_url, cinema in cinemas.items():
            if 'barnsley' in cinema_url:
                # special logic for Barnsley which uses its own website system
                showings += get_showings(cinema_url, cinema)
            else:
                showings += lpvs_get_showings(Parkway.CHAIN, cinema_url, cinema)
        return showings
