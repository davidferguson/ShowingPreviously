import pytz

from showingpreviously.db import add_chain, add_cinema, add_screen, add_film, add_showing
from showingpreviously.model import Showing, ChainArchiver
from showingpreviously.selenium import close_selenium_webdriver

# import cinemas here, and add them to the all_cinema_chains list
from showingpreviously.cinemas.cineworld import Cineworld
from showingpreviously.cinemas.dundee_contemporary_arts import DundeeContemporaryArts
from showingpreviously.cinemas.empire import Empire
from showingpreviously.cinemas.isle_of_bute_discovery_centre_cinema import IsleOfButeDiscoveryCentreCinema
from showingpreviously.cinemas.vista_system import Odeon, Curzon
from showingpreviously.cinemas.omniplex import Omniplex
from showingpreviously.cinemas.picturehouse import Picturehouse
from showingpreviously.cinemas.lpvs import TheLight
from showingpreviously.cinemas.parkway import Parkway
from showingpreviously.cinemas.vue import Vue

all_cinema_chains = [
    Cineworld(),
    Curzon(),
    DundeeContemporaryArts(),
    Empire(),
    IsleOfButeDiscoveryCentreCinema(),
    Odeon(),
    Omniplex(),
    Parkway(),
    Picturehouse(),
    TheLight(),
    Vue(),
]


def process_showing(showing: Showing, dry_run: bool = False):
    film = showing.film
    time = showing.time
    chain = showing.chain
    cinema = showing.cinema
    screen = showing.screen
    json_attributes = showing.json_attributes

    timezone = pytz.timezone(cinema.timezone)
    utc_time = timezone.localize(time).astimezone(pytz.timezone('UTC'))

    if not dry_run:
        add_chain(chain.name)
        add_cinema(chain.name, cinema.name, cinema.timezone)
        add_screen(chain.name, cinema.name, screen.name)
        add_film(film.name, film.year)
        add_showing(film.name, film.year, chain.name, cinema.name, screen.name, utc_time, json_attributes)


def run_chain(chain: ChainArchiver, dry_run: bool = False):
    showings = chain.get_showings()
    for showing in showings:
        process_showing(showing, dry_run)


def run_all(dry_run: bool = False) -> None:
    for cinema_chain in all_cinema_chains:
        run_chain(cinema_chain, dry_run)
    close_selenium_webdriver()


def run_single(name: str, dry_run: bool = False) -> None:
    for cinema_chain in all_cinema_chains:
        if type(cinema_chain).__name__ == name:
            run_chain(cinema_chain, dry_run)
    close_selenium_webdriver()
