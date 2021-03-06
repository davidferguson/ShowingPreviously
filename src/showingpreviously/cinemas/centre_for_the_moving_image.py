from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE, UNKNOWN_FILM_YEAR
import showingpreviously.requests as requests

import datetime
from bs4 import BeautifulSoup


DAYS_PREVIOUS = 3


CHAIN = Chain(name='Centre for the Moving Image')
EDINBURGH_CINEMA = Cinema(name='Filmhouse Edinburgh', timezone=UK_TIMEZONE)
BELMONT_CINEMA = Cinema(name='Belmont Filmhouse', timezone=UK_TIMEZONE)


KNOWN_SHOWING_TYPE_ATTRIBUTES = [
    'audio-described',
    'subtitled',
    'captioned',
    'carers-and-babies',
    'three-d',
]


CINEMAS_LIST = [
    {'base_url': 'https://www.filmhousecinema.com', 'cinema': EDINBURGH_CINEMA},
    {'base_url': 'https://www.belmontfilmhouse.com', 'cinema': BELMONT_CINEMA},
]


film_page_details_cache = {}

def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_days_to_fetch() -> [datetime.datetime]:
    # Fetch films from the range of (today - DAYS_PREVIOUS) to today
    base = datetime.date.today()
    date_list = [base - datetime.timedelta(days=x) for x in range(DAYS_PREVIOUS)]
    return date_list


def get_showings_for_date(cinema: dict[str, any], fetch_date: datetime.date) -> [Showing]:
    showings = []
    fetch_date_str = fetch_date.strftime('%Y-%m-%d')
    whats_on_url = f'{cinema["base_url"]}/whats-on/{fetch_date_str}'
    req = get_response(whats_on_url)
    soup = BeautifulSoup(req.text, features='html.parser')
    showings_class = soup.find('div', class_='whats-on-list')
    for showing_item in showings_class.find_all('div', class_='stub-details'):
        showings += get_showing_item(cinema, fetch_date_str, showing_item)
    return showings


def get_showing_item(cinema: dict[str, any], showing_date_str: str, showing_item: BeautifulSoup) -> [Showing]:
    showing_list = []
    name = showing_item.find('span', class_='field--name-title').text
    more_info_link = showing_item.find('a', class_='btn-more-info')['href']
    release_year, attributes = get_film_page_details(cinema, more_info_link)
    showing_times = showing_item.find('div', class_='screening-times-btns')
    film = Film(name=name, year=release_year)
    if film.name.lower().endswith(' (baby + carer)'):
        film.name = film.name[:-len(' (baby + carer)')]
        attributes['carers-and-babies'] = True
    if film.name.lower().startswith('senior selections: '):
        film.name = film.name[len('senior selections: '):]
        attributes['seniors'] = True
    for showing_time in showing_times.find_all('a', class_='btn-times'):
        showing_time_str = showing_time.text.strip().split('\n')[0].strip()
        showing_screen = Screen(name=showing_time.find('span', class_='screen').text.strip())
        if showing_time_str == 'Watch Now' or showing_screen.name == 'On Demand':
            # Do not include On-Demand showings (through the Filmhouse at Home streaming service)
            continue
        showing_datetime = datetime.datetime.strptime(f'{showing_date_str} {showing_time_str}', '%Y-%m-%d %H:%M')
        showing_type_attributes = get_showing_type_attributes(name, showing_date_str, showing_time)
        # Special case for 3D screenings, which should be treated as a format and not as a separate attribute
        if 'three-d' in showing_type_attributes:
            if 'format' not in attributes:
                attributes['format'] = []
            attributes['format'].append('3d')
            del showing_type_attributes['three-d']
        showing = Showing(
            film=film,
            time=showing_datetime,
            chain=CHAIN,
            cinema=cinema['cinema'],
            screen=showing_screen,
            json_attributes={**attributes, **showing_type_attributes}
        )
        showing_list.append(showing)
    return showing_list


def get_showing_type_attributes(film_name: str, showing_date_str: str, showing: BeautifulSoup) -> dict[str, any]:
    showing_type_list = showing.find_all('span', class_='showing-type')
    attributes = {}
    for showing_type in showing_type_list:
        showing_type_attribute = [attr for attr in showing_type['class'] if attr != 'showing-type']
        if len(showing_type_attribute) != 1:
            raise CinemaArchiverException(f'Expected one showing type attribute for {film_name} on {showing_date_str}: {str(showing_type_attribute)}')
        showing_type_attribute = showing_type_attribute[0]
        if showing_type_attribute not in KNOWN_SHOWING_TYPE_ATTRIBUTES:
            raise CinemaArchiverException(f'Unknown showing type attribute for {film_name} on {showing_date_str}: {showing_type_attribute}')
        attributes[showing_type_attribute] = True
    return attributes


def get_film_page_details(cinema: dict[str, any], film_url: str) -> (str, dict[str, any]):
    global film_page_details_cache
    if not film_url.startswith('http'):
        film_url = f'{cinema["base_url"]}{film_url}'
    if film_url in film_page_details_cache:
        film_details = film_page_details_cache[film_url]
        return film_details
    req = requests.get(film_url)
    if req.status_code not in [200, 403]:
        raise CinemaArchiverException(f'Got status code {req.status_code} when fetching URL {film_url}')
    soup = BeautifulSoup(req.text, features='html.parser')
    page_title = soup.find('title').text
    release_year = UNKNOWN_FILM_YEAR
    attributes = {}
    if req.status_code != 403 and 'Access Denied' not in page_title:
        details_list = soup.find('div', class_='event-detail')
        release_year = get_specific_film_attribute(details_list, 'release_year')
        attributes['language'] = get_specific_film_attribute(details_list, 'languages')
        filmFormat =  get_specific_film_attribute(details_list, 'format')
        if filmFormat != '':
            attributes['format'] = [filmFormat]
    film_page_details_cache[film_url] = (release_year, attributes)
    return release_year, attributes


def get_specific_film_attribute(details_list: BeautifulSoup, attribute_name: str) -> str:
    attribute_soup = details_list.find('li', class_=attribute_name)
    if attribute_soup is None:
        return ''
    attribute_value = attribute_soup.find('p').text.strip().lower()
    return attribute_value


class CentreForTheMovingImage(ChainArchiver):
    def get_showings(self) -> [Showing]:
        global film_page_details_cache
        film_page_details_cache = {}
        showings = []
        for cinema in CINEMAS_LIST:
            for fetch_date in get_days_to_fetch():
                showings += get_showings_for_date(cinema, fetch_date)
        return showings
