import pytz

from showingpreviously.db import add_chain, add_cinema, add_screen, add_film, add_showing
from showingpreviously.model import Showing, ChainArchiver
from showingpreviously.selenium import close_selenium_webdriver

# import cinemas here, and add them to the all_cinema_chains list
from showingpreviously.cinemas.centre_for_the_moving_image import CentreForTheMovingImage
from showingpreviously.cinemas.cineworld import Cineworld
from showingpreviously.cinemas.dominion import Dominion
from showingpreviously.cinemas.dundee_contemporary_arts import DundeeContemporaryArts
from showingpreviously.cinemas.empire import Empire
from showingpreviously.cinemas.vista_system import Odeon, Curzon
from showingpreviously.cinemas.picturehouse import Picturehouse
from showingpreviously.cinemas.lpvs import TheLight
from showingpreviously.cinemas.parkway import Parkway
from showingpreviously.cinemas.vue import Vue

all_cinema_chains = [
    CentreForTheMovingImage(),
    Cineworld(),
    Curzon(),
    Dominion(),
    DundeeContemporaryArts(),
    Empire(),
    Odeon(),
    Parkway(),
    Picturehouse(),
    TheLight(),
    Vue(),
]


def process_showing(showing: Showing):
    film = showing.film
    time = showing.time
    chain = showing.chain
    cinema = showing.cinema
    screen = showing.screen
    json_attributes = showing.json_attributes

    timezone = pytz.timezone(cinema.timezone)
    utc_time = timezone.localize(time).astimezone(pytz.timezone('UTC'))

    add_chain(chain.name)
    add_cinema(chain.name, cinema.name, cinema.timezone)
    add_screen(chain.name, cinema.name, screen.name)
    add_film(film.name, film.year)
    add_showing(film.name, film.year, chain.name, cinema.name, screen.name, utc_time, json_attributes)


def run_chain(chain: ChainArchiver):
    showings = chain.get_showings()
    for showing in showings:
        process_showing(showing)


def run_all() -> None:
    for cinema_chain in all_cinema_chains:
        run_chain(cinema_chain)
    close_selenium_webdriver()


def run_single(name: str) -> None:
    for cinema_chain in all_cinema_chains:
        if type(cinema_chain).__name__ == name:
            run_chain(cinema_chain)
    close_selenium_webdriver()
