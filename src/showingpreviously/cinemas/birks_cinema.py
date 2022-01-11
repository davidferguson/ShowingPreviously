import re
import bs4
import datetime

import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE, UNKNOWN_FILM_YEAR

BASE_URL = 'https://birkscinema.co.uk'
FILM_SCHEDULE_URL = 'https://birkscinema.co.uk/whats-on/on-screen/#dates'
FILM_NAME_IGNORES = []

CHAIN = Chain('The Birks Cinema')
CINEMA = Cinema('The Birks Cinema', UK_TIMEZONE)
SCREEN = Screen('Screen 1')

film_year_cache = {}


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def format_film_name(film_name: str) -> (str, dict[str, any]):
    attributes = {'format': []}
    # convert to lowercase for easier processing
    film_name = film_name.lower()
    # check to see if this is a live event
    if film_name.startswith('national theatre live: '):
        attributes['format'].append('live')
        attributes['event'] = True
        film_name = film_name.replace('national theatre live: ', '')
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
    # remove an empty format attribute
    if len(attributes['format']) == 0:
        del attributes['format']
    # return the formatted name and attributes
    return film_name, attributes


def get_film_year(showing_item: bs4.element.Tag) -> str:
    global film_year_cache
    # extract the 'whats on' link from the showing item
    if len(list(showing_item.children)) != 2:
        return UNKNOWN_FILM_YEAR
    whats_on_href = list(showing_item.children)[1].find('a')['href']
    if not whats_on_href.startswith('/whats-on/on-screen/'):
        return UNKNOWN_FILM_YEAR
    whats_on_url = f'{BASE_URL}{whats_on_href}'
    # see if the year exists in the cache already
    if whats_on_url in film_year_cache:
        return film_year_cache[whats_on_url]
    # fetch the film year
    resp = get_response(whats_on_url)
    soup = bs4.BeautifulSoup(resp.text, 'html.parser')
    main_text = soup.find('div', class_='main').text
    regex_results = re.findall(r'Released: (\d\d\d\d)', main_text)
    future_year = int(datetime.datetime.now().strftime('%Y')) + 5
    if len(regex_results) == 1 and 1800 < int(regex_results[0]) < future_year:
        film_year = regex_results[0]
    else:
        film_year = UNKNOWN_FILM_YEAR
    # save the film year into the cache
    film_year_cache[whats_on_url] = film_year
    # return the film year
    return film_year


class BirksCinema(ChainArchiver):
    def get_showings(self) -> [Showing]:
        global film_year_cache
        film_year_cache = {}
        showings = []
        resp = get_response(FILM_SCHEDULE_URL)
        soup = bs4.BeautifulSoup(resp.text, 'html.parser')
        showings_divs = soup.select('div[x-show="tab === \'dates\'"]')
        if len(showings_divs) != 1:
            raise CinemaArchiverException(f'Expected a single showings div, found {len(showings_divs)}')
        showings_div = showings_divs[0]
        for showing_date_group in showings_div.find_all('div', class_='mb-6 pb-6 border-primary border-b border-opacity-50'):
            for showing_item in showing_date_group.find_all('li'):
                showing_time_str = showing_item['data-startdate']
                # despite looking like a UTC-formatted time (with the trailing 'Z')
                # this time is actually local time, ie: it adjusts to British Summer Time
                showing_time = datetime.datetime.strptime(showing_time_str, '%Y-%m-%dT%H:%M:%SZ')
                film_name_tags = showing_item.select('a[title]')
                if len(film_name_tags) != 1:
                    raise CinemaArchiverException(f'Expected a single film name tag, found {len(film_name_tags)}')
                film_name, film_name_attributes = format_film_name(film_name_tags[0]['title'])
                film_year = get_film_year(showing_item)
                film = Film(film_name, film_year)
                showing = Showing(
                    film=film,
                    time=showing_time,
                    chain=CHAIN,
                    cinema=CINEMA,
                    screen=SCREEN,
                    json_attributes={**film_name_attributes}
                )
                showings.append(showing)
        return showings
