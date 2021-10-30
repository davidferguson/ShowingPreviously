from datetime import datetime


class Chain:
    def __init__(self, name: str) -> None:
        self.name = name.strip()

    def __repr__(self) -> str:
        return f'Chain "{self.name}"'


class Cinema:
    def __init__(self, name: str, timezone: str) -> None:
        self.name = name.strip()
        self.timezone = timezone

    def __repr__(self) -> str:
        return f'Cinema "{self.name}"'


class Screen:
    def __init__(self, name: str) -> None:
        self.name = name.strip()

    def __repr__(self) -> str:
        return f'Screen "{self.name}"'


class Film:
    def __init__(self, name: str, year: str) -> None:
        self.name = name.strip()
        self.year = str(year).strip()

    def __repr__(self) -> str:
        return f'Film "{self.name}" ({self.year})'


class Showing:
    def __init__(self, film: Film, time: datetime, chain: Chain, cinema: Cinema, screen: Screen,
                 json_attributes: dict[str, str]) -> None:
        self.film = film
        self.time = time
        self.chain = chain
        self.cinema = cinema
        self.screen = screen
        self.json_attributes = json_attributes

    def __repr__(self) -> str:
        return f'Showing of {self.film} at {self.chain}, {self.cinema}, {self.screen}, on {self.time.strftime("%Y-%m-%d %H:%M")}'


class ChainArchiver:
    def get_showings(self) -> [Showing]:
        pass


class CinemaArchiverException(Exception):
    pass
