from showingpreviously.model import Chain, Cinema, Screen, Film, Showing, ChainArchiver, CinemaArchiverException
from showingpreviously.consts import UNKNOWN_FILM_YEAR, STANDARD_DAYS_AHEAD, UK_TIMEZONE
import showingpreviously.requests as requests

import datetime, json, re, pytz, bs4

CHAIN = Chain(name='Glasgow Film Theatre')
CINEMA = Cinema(name='Glasgow Film Theatre', timezone=UK_TIMEZONE)

BASE_URL = 'https://glasgowfilm.org'
WHATS_ON_URL = 'https://glasgowfilm.org/whats-on/all'
FILM_TITLE_IGNORES = ['take 2:', 'introduction & q&a', 'preview:', 'panel discussion', 'discussion', 'recorded Q&A', 'Q&A', 'access film club:', 'visible cinema:', 'movie memories:', 'recorded introduction']


films_cache = {}


class GlasgowFilmTheatre(ChainArchiver):
    def get_showings(self):
        global films_cache
        films_cache = {}
        showings = []
        req = get_response(WHATS_ON_URL)
        soup = bs4.BeautifulSoup(req.text, 'html.parser')
        current_year = datetime.datetime.now().year
        for showings_on_date in soup.find_all('div', class_='show-strip-group'):
            #showing_date_str = showings_on_date.find('div, class_='show-strip-group-date').text.strip()
            #if showing_date_str.lower() == 'today':
            #    # dealing with 'today' is complicated, because the archiver could be running
            #    # in a timezone different to that of the cinema, and so the date of 'today'
            #    # for the cinema may be different to the 'today' of the archiver
            #    showing_date_str = datetime.datetime.now(pytz.timezone(CINEMA.timezone)).strftime('%a %-d %B')
            for showing_film in showings_on_date.find_all('div', class_='show-strip'):
                film_heading = showing_film.find('div', class_='show-strip-heading')
                film, film_attributes = film_from_heading(film_heading)
                if 'Audio description available' in showing_film.text:
                    film_attributes['audio-described'] = True
                for showing_item in showing_film.find_all('li', class_='instance'):
                    if 'instance-online' in showing_item['class']:
                        # ignore online-only showings
                        continue
                    showing_datetime = datetime.datetime.fromtimestamp(int(showing_item['data-timestamp']))
                    showing_screen = Screen(showing_item['data-instance-venue'])
                    showing_attributes = get_showing_attributes(showing_item)
                    showing = Showing(
                        film = film,
                        time = showing_datetime,
                        chain = CHAIN,
                        cinema = CINEMA,
                        screen = showing_screen,
                        json_attributes = {**film_attributes, **showing_attributes}
                    )
                    showings.append(showing)
        return showings


def get_response(url: str) -> requests.Response:
    r = requests.get(url)
    if r.status_code != 200:
        raise CinemaArchiverException(f'Got status code {r.status_code} when fetching URL {url}')
    return r


def parse_film_title(film_title: str) -> (str, dict[str, any]):
    # use lowercase
    film_title = film_title.lower()
    film_attributes = {'format': []}
    # strip the rating from the film
    # note: the rating is always last
    if film_title.find('(') != -1:
        film_title = film_title[:film_title.find('(')]
    # check for ignore keywords
    for keyword in FILM_TITLE_IGNORES:
        if keyword.lower() in film_title:
            film_title = film_title.replace(keyword.lower(), '')
    # check for 4K screenings
    if '4k' in film_title:
        film_attributes['format'] += ['digital', '4K']
        film_title = film_title.replace('4k', '').strip()
    # check for 35mm screenings
    if '35mm' in film_title:
        film_attributes['format'].append('35mm')
        film_title = film_title.replace('35mm', '').strip()
    # if no format is given, assume digital
    if len(film_attributes['format']) == 0:
        film_attributes['format'] = ['digital']
    # clean up the title by removing trailing characters,
    # blank spaces and double-spaces
    while True:
        # assume no changes
        old_title = film_title
        # remove any trailing '+' or '-'
        if film_title.strip().endswith('-') or film_title.strip().endswith('+'):
            film_title = film_title.strip()[:-1]
        # remove any double-spaces from removing two items from the title
        film_title = film_title.replace('  ', ' ').strip()
        if old_title == film_title:
            break
    return film_title, film_attributes
    

def film_from_heading(film_heading: bs4.element.Tag) -> (Film, dict[str, any]):
    global films_cache
    film_title, film_attributes = parse_film_title(film_heading.find('h3').text)
    if film_title in films_cache:
        return films_cache[film_title]
    film = None
    film_details_page_url = f'{BASE_URL}{film_heading.find("h3").find("a")["href"]}'
    film_details_page = get_response(film_details_page_url).text
    soup = bs4.BeautifulSoup(film_details_page, 'html.parser')
    try:
        metadata = soup.select('ul.inline-grid-row.meta')[0]
    except IndexError:
        film = Film(name=film_title, year=UNKNOWN_FILM_YEAR)
        films_cache[film_title] = film, {}
        return film, {}
    for meta_item in metadata.find_all('li'):
        meta_label = meta_item.find('span', class_='meta-label').text.strip()
        meta_value = meta_item.find('span', class_='meta-value').text.strip()
        if meta_label == 'Year of Production':
            film = Film(name=film_title, year=meta_value)
        if meta_label == 'Language':
            with_subtitles = re.match('([a-zA-Z ]+)with ([a-zA-Z ]+) subtitles', meta_value)
            if with_subtitles:
                film_attributes['language'] = with_subtitles.group(1).strip()
                film_attributes['subtitled'] = with_subtitles.group(2).strip()
            else:
                film_attributes['language'] = meta_value
    if film == None:
        film = Film(name=film_title, year=UNKNOWN_FILM_YEAR)
    films_cache[film_title] = film, film_attributes
    return film, film_attributes


def get_showing_attributes(showing_event: bs4.element.Tag) -> dict[str, any]:
    showing_attributes = {}
    for attr in showing_event.find_all('span', class_='instance-type'):
        attr_name = attr.find('span', class_='accessible-hide').text.strip()
        if attr_name == 'Captioned':
            showing_attributes['captioned'] = True
        elif attr_name == 'Autism friendly':
            showing_attributes['autism-friendly'] = True
        elif attr_name == 'Dementia friendly':
            showing_attributes['dementia-friendly'] = True
        else:
            raise Exception(f'Unknown attribute {attr_name}')
    return showing_attributes

