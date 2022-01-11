import datetime
from bs4 import BeautifulSoup

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE, UNKNOWN_FILM_YEAR


FILM_SCHEDULE_URL = 'https://www.dominioncinema.co.uk/schedule/'
FILM_NAME_IGNORES = ['(live)']

CHAIN = Chain('Dominion')
CINEMA = Cinema('Dominion', UK_TIMEZONE)


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def format_film_name(film_name: str) -> str:
    # convert to lowercase for easier processing
    film_name = film_name.lower()
    # remove all the ignore items from the film name
    for ignore_item in FILM_NAME_IGNORES:
        if ignore_item in film_name:
            film_name = film_name.replace(ignore_item, '')
    # tidy up the film name after ignore removal
    while True:
        # assume no changes
        old_name = film_name
        # remove any double-spaces from removing two items from the title
        film_name = film_name.replace('  ', ' ').strip()
        if old_name == film_name:
            break
    # return the formatted name
    return film_name


class Dominion(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        resp = get_response(FILM_SCHEDULE_URL)
        soup = BeautifulSoup(resp.text, 'html.parser')
        schedule_table_body = soup.find('table', class_='schedule').find('tbody')
        for schedule_item in schedule_table_body.find_all('tr'):
            showing_date_str = schedule_item.find_all('td')[0].text
            showing_screen = Screen(schedule_item.find_all('td')[1].text)
            # 'First Class' is an add-on package, not a separate screen
            if showing_screen.name == 'First Class and Gold One':
                showing_screen.name = 'Gold One'
            film_name = format_film_name(schedule_item.find_all('td')[2].text)
            film = Film(film_name, UNKNOWN_FILM_YEAR)
            showing_time_str = schedule_item.find_all('td')[3].find('div', class_='time').text
            showing_time = datetime.datetime.strptime(f'{showing_time_str} {showing_date_str}', '%H:%M %a %d %b, %Y')
            showing = Showing(
                film=film,
                time=showing_time,
                chain=CHAIN,
                cinema=CINEMA,
                screen=showing_screen,
                json_attributes={}
            )
            showings.append(showing)
        return showings
