from datetime import datetime


class Chain:
    def __init__(self, name: str) -> None:
        self.name = name


class Cinema:
    def __init__(self, name: str, timezone: str, started_archiving: datetime) -> None:
        self.name = name
        self.timezone = timezone
        self.started_archiving = started_archiving


class Screen:
    def __init__(self, name: str) -> None:
        self.name = name


class Film:
    def __init__(self, name: str, year: int) -> None:
        self.name = name
        self.year = year


class Showing:
    def __init__(self, film: Film, time: datetime, chain: Chain, cinema: Cinema, screen: Screen,
                 json_attributes: dict[str, str]) -> None:
        self.film = film
        self.time = time
        self.chain = chain
        self.cinema = cinema
        self.screen = screen
        self.json_attributes = json_attributes


class ChainArchiver:
    def get_showings(self) -> [Showing]:
        pass


class CinemaArchiverException(Exception):
    pass
