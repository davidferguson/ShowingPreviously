from typing import Optional

import click

from showingpreviously.archiver import run_all, run_single, all_cinema_chains
from showingpreviously.db import db_info, database_location


@click.group()
def cli() -> None:
    pass


@cli.command('info')
def info_cmd() -> None:
    """Prints basic information about showingpreviously, and the database contents"""
    print('ShowingPreviously: A cinema showtimes archiver')
    print('The database is stored at "%s".' % database_location)
    print('There are %s cinema chains installed' % len(all_cinema_chains))
    print('In the database we have %s chains, with %s cinemas and %s screens, and %s films.' % db_info())


@cli.command('run')
@click.option('--chain', default=None, show_default=True, type=click.STRING, help='The archiver class name to run')
def run_cmd(chain: Optional[str]) -> None:
    """Runs the archiver on all cinema chains"""
    if chain is None:
        run_all()
    else:
        run_single(chain)


if __name__ == '__main__':
    cli()
