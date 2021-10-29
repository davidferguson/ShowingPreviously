import pytz

from showingpreviously.db import add_chain, add_cinema, add_screen, add_film, add_showing
from showingpreviously.model import Showing

# import cinemas here, and add them to the all_cinema_chains list
from showingpreviously.cinemas.dundee_contemporary_arts import DundeeContemporaryArts

all_cinema_chains = [
    DundeeContemporaryArts(),
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


def run_all() -> None:
    for cinema_chain in all_cinema_chains:
        showings = cinema_chain.get_showings()
        for showing in showings:
            process_showing(showing)
