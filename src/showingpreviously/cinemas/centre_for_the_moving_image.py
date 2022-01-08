from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing
from showingpreviously.consts import UK_TIMEZONE, UNKNOWN_FILM_YEAR, STANDARD_DAYS_AHEAD
import showingpreviously.requests as requests

import datetime
from bs4 import BeautifulSoup
from typing import Iterator


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
    'format-35mm',
    'format-70mm',
    'format-digital',
]

KNOWN_SHOWING_FORMATS = [
    '70mm',
    '35mm',
    'digital',
]

DEFAULT_SHOWING_FORMAT = 'digital'

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


def get_showing_dates() -> Iterator[datetime.datetime]:
    # start from tomorrow, not today, since the Filmhouse shows *all* the showings
    # for a given day, including those that have already happened, and those can
    # break the archiver if we need to fetch the booking info for them
    current_date = datetime.date.today() + datetime.timedelta(days=1)
    end_date = current_date + datetime.timedelta(days=STANDARD_DAYS_AHEAD)
    while current_date < end_date:
        yield current_date
        current_date += datetime.timedelta(days=1)


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
    film_name = showing_item.find('span', class_='field--name-title').text
    more_info_link = showing_item.find('a', class_='btn-more-info')['href']
    release_year, film_attributes = get_film_page_details(cinema, more_info_link)
    showing_times = showing_item.find('div', class_='screening-times-btns')
    film_name = extract_attributes_from_name(film_name, film_attributes)
    film = Film(name=film_name, year=release_year)

    for showing_time in showing_times.find_all('a', class_='btn-times'):
        showing_time_str = showing_time.text.strip().split('\n')[0].strip()
        showing_screen = Screen(name=showing_time.find('span', class_='screen').text.strip())
        if showing_time_str == 'Watch Now' or showing_screen.name == 'On Demand' or showing_screen.name == 'Virtual Cinema':
            # Do not include On-Demand showings (through the Filmhouse at Home streaming service)
            continue
        showing_datetime = datetime.datetime.strptime(f'{showing_date_str} {showing_time_str}', '%Y-%m-%d %H:%M')
        showing_attributes = get_showing_type_attributes(film_name, showing_date_str, showing_time)
        showing_attributes['format'] = determine_showing_format(cinema['base_url'], showing_time['data-eventid'], film_attributes, showing_attributes)

        # Special case for 3D screenings, which should be treated as a format and not as a separate attribute
        if 'three-d' in showing_attributes:
            showing_attributes['format'].append('3d')
            del showing_attributes['three-d']

        showing = Showing(
            film=film,
            time=showing_datetime,
            chain=CHAIN,
            cinema=cinema['cinema'],
            screen=showing_screen,
            json_attributes={**film_attributes, **showing_attributes}
        )
        showing_list.append(showing)
    return showing_list


def extract_attributes_from_name(film_name: str, film_attributes: dict[str, any]) -> str:
    if film_name.lower().endswith(' (baby + carer)'):
        film_name = film_name[:-len(' (baby + carer)')]
        film_attributes['carers-and-babies'] = True
    if film_name.lower().startswith('senior selections: '):
        film_name = film_name[len('senior selections: '):]
        film_attributes['seniors'] = True
    if film_name.lower().endswith(' (35mm)'):
        film_name = film_name[:-len(' (35mm)')]
        film_attributes['format'].append('35mm')
    if film_name.lower().endswith(' (70mm)'):
        film_name = film_name[:-len(' (70mm)')]
        film_attributes['format'].append('70mm')
    if film_name.lower().endswith(' (35mm and 70mm)'):
        film_name = film_name[:-len(' (35mm and 70mm)')]
        film_attributes['format'] += ['35mm', '70mm']
    if film_name.lower().endswith(' (70mm and 35mm)'):
        film_name = film_name[:-len(' (70mm and 35mm)')]
        film_attributes['format'] += ['35mm', '70mm']
    if film_name.lower().endswith(' (35mm and digital)'):
        film_name = film_name[:-len(' (35mm and digital)')]
        film_attributes['format'] += ['35mm', 'digital']
    if film_name.lower().endswith(' (digital and 35mm)'):
        film_name = film_name[:-len(' (digital and 35mm)')]
        film_attributes['format'] += ['35mm', 'digital']
    if film_name.lower().endswith(' (70mm and digital)'):
        film_name = film_name[:-len(' (70mm and digital)')]
        film_attributes['format'] += ['70mm', 'digital']
    if film_name.lower().endswith(' (digital and 70mm)'):
        film_name = film_name[:-len(' (digital and 70mm)')]
        film_attributes['format'] += ['35mm', 'digital']
    return film_name


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
        film_format = get_specific_film_attribute(details_list, 'format')
        if film_format != '':
            attributes['format'] = [film_format]
        else:
            attributes['format'] = [DEFAULT_SHOWING_FORMAT]
    film_page_details_cache[film_url] = (release_year, attributes)
    return release_year, attributes


def get_specific_film_attribute(details_list: BeautifulSoup, attribute_name: str) -> str:
    attribute_soup = details_list.find('li', class_=attribute_name)
    if attribute_soup is None:
        return ''
    attribute_value = attribute_soup.find('p').text.strip().lower()
    return attribute_value


def determine_showing_format(base_url: str, event_id: str, film_attributes: dict[str, any], showing_attributes: dict[str, any]) -> [str]:
    # if the format is explicitly specified in the showing_attributes, use that
    if 'format-35mm' in showing_attributes:
        del showing_attributes['format-35mm']
        return ['35mm']
    elif 'format-70mm' in showing_attributes:
        del showing_attributes['format-70mm']
        return ['70mm']
    elif 'format-digital' in showing_attributes:
        del showing_attributes['format-digital']
        return ['70mm']

    # determine all the known formats for this film
    film_formats = [format_type for format_type in KNOWN_SHOWING_FORMATS if 'format' in film_attributes and format_type in ' '.join(film_attributes['format'])]

    # if only a single format is specified in the film_attributes, use that
    if len(film_formats) == 1:
        return film_formats

    # if no format is specified in film_attributes, assume the default
    elif len(film_formats) == 0:
        return [DEFAULT_SHOWING_FORMAT]

    # if multiple formats are specified in film_attributes, check the booking page
    elif len(film_formats) > 1:
        booking_url = f'{base_url}/boxoffice/?event={event_id}'
        req = get_response(booking_url)
        booking_soup = BeautifulSoup(req.text, features='html.parser')
        page_title = booking_soup.find('title').text
        showing_formats = [film_format for film_format in film_formats if film_format in page_title]
        if len(showing_formats) == 0:
            return [DEFAULT_SHOWING_FORMAT]
        else:
            return showing_formats


class CentreForTheMovingImage(ChainArchiver):
    def get_showings(self) -> [Showing]:
        global film_page_details_cache
        film_page_details_cache = {}
        showings = []
        for cinema in CINEMAS_LIST:
            for fetch_date in get_showing_dates():
                showings += get_showings_for_date(cinema, fetch_date)
        return showings
