from bs4 import BeautifulSoup
import re

from datetime import datetime, timedelta
import showingpreviously.requests as requests
from showingpreviously.model import ChainArchiver, CinemaArchiverException, Chain, Cinema, Screen, Film, Showing

CINEMAS_URL = 'https://www.empirecinemas.co.uk/select_cinema_first/ci/'
SHOWINGS_URL = 'https://www.empirecinemas.co.uk/?page=nowshowing&tbx_site_id={cinema_id}&scope={date}'

DAYS_AHEAD = 2
CHAIN = Chain('Empire Cinemas')
SUBTITLE_LINK_PATTERN = re.compile(r'\'(?P<booking_link>https?://.+?)\'')


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def get_cinemas() -> dict[str, Cinema]:
    r = get_response(CINEMAS_URL)
    soup = BeautifulSoup(r.text, features='html.parser')
    selector = soup.find('select', {'name': 'tbx_site_id'})
    cinemas = {}
    for option in selector.find_all('option'):
        id = option['value']
        if id == '':
            continue
        name = option.text
        cinemas[id] = Cinema(name, 'Europe/London')
    return cinemas


def get_showing_dates() -> str:
    current_date = datetime.now()
    end_date = current_date + timedelta(days=DAYS_AHEAD)
    while current_date < end_date:
        yield current_date.strftime('%d/%m/%Y')
        current_date += timedelta(days=1)


def get_json_attributes_from_images(images: [any]) -> dict[str, any]:
    if images is None:
        return {}
    attributes = {'format': []}
    for image in images:
        if image['alt'] == 'Audio Described Available':
            attributes['audio-described'] = True
        elif image['alt'] in ['D-Box', 'IMPACT®', 'IMAX']:
            attributes['format'].append(image['alt'])
        elif image['alt'] == 'Broadcast Live!':
            attributes['format'].append('Live')
        elif image['alt'] == 'Subtitled':
            attributes['subtitled'] = True
        elif image['alt'] == 'EMPIRE Jnrs':
            attributes['carers-and-babies'] = True
        elif image['alt'] == 'EMPIRE Seniors':
            attributes['senior'] = True
    if len(attributes['format']) == 0:
        del attributes['format']
    return attributes


def get_date_and_time(date: str, time: str) -> datetime:
    timestamp_string = f'{date} {time}'
    format_string = '%d/%m/%Y %H:%M'
    try:
        timestamp = datetime.strptime(timestamp_string, format_string)
        return timestamp
    except ValueError:
        raise CinemaArchiverException(f'Error parsing timestamp "{timestamp_string}"')


film_cache = {}


def get_film(url: str, title: str) -> Film:
    global film_cache
    if url in film_cache:
        return film_cache[url]
    r = get_response(f'https://www.empirecinemas.co.uk/{url}')
    soup = BeautifulSoup(r.text, features='html.parser')
    metadata = soup.find('div', {'class': 'info-section'}).find('dl')
    release_date = metadata.find('dt', text='Release Date:').findNext('dd').text
    year = release_date.strip()[-4:]
    film = Film(title, year)
    film_cache[url] = film
    return film


def get_screen(showing) -> Screen:
    booking_link = showing.find('a', {'href': True})
    continue_btn = showing.find('input', {'type': 'button', 'value': 'Continue'})
    if continue_btn is not None:
        continue_js = continue_btn['onclick']
        booking_link_href = SUBTITLE_LINK_PATTERN.search(continue_js).group('booking_link')
    else:
        booking_link_href = booking_link['href']
    r = get_response(booking_link_href)
    soup = BeautifulSoup(r.text, features='html.parser')
    for info in soup.find_all('p', {'class': 'info'}):
        if info.text.lower().startswith('in auditorium: '):
            screen_name = info.text[15:]
            return Screen(screen_name)


def get_showings_on_date(date: str, cinema_id: str, cinema: Cinema):
    url = SHOWINGS_URL.format(cinema_id=cinema_id, date=date)
    r = get_response(url)
    soup = BeautifulSoup(r.text, features='html.parser')
    showings = []
    for film_block in soup.find_all('div', {'class': 'filmpack'}):
        info = film_block.find('div', {'class': 'infos'})
        film_title = info.find('h2').text
        film_url = info.find('a')['href']
        film = get_film(film_url, film_title)
        showing_list = film_block.find('ul', {'class': 'filmlist'})
        for showing in showing_list.find_all('li'):
            time = showing.find('div', {'class': 'time'}).find('a').text
            date_and_time = get_date_and_time(date, time)
            json_attributes = get_json_attributes_from_images(showing.find_all('img'))
            screen = get_screen(showing)
            showing = Showing(film, date_and_time, CHAIN, cinema, screen, json_attributes)
            showings.append(showing)
    return showings


class Empire(ChainArchiver):
    def get_showings(self) -> [Showing]:
        showings = []
        cinemas = get_cinemas()
        for date in get_showing_dates():
            for cinema_id, cinema in cinemas.items():
                showings += get_showings_on_date(date, cinema_id, cinema)
        return showings
