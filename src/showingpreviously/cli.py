from typing import Optional

import click

from showingpreviously.archiver import run_all, run_single, all_cinema_chains
from showingpreviously.db import db_info, database_location


@click.group()
def cli() -> None:
    pass


@cli.command('info')
@click.option('--list-chains', 'list_chains', is_flag=True, default=False, show_default=False, type=click.BOOL, help='List all the chains that can be run with the --chain option')
def info_cmd(list_chains: bool) -> None:
    """Prints basic information about showingpreviously, and the database contents"""
    print('ShowingPreviously: A cinema showtimes archiver')
    print(f'The database is stored at "{database_location}".')
    print(f'There are {len(all_cinema_chains)} cinema chains installed')
    chains_count, cinema_count, screen_count, film_count, showing_count = db_info()
    print(f'In the database we have {chains_count} chains, with {cinema_count} cinemas and {screen_count} screens, {film_count} films and {showing_count} showings.')
    if list_chains:
        installed_chains = ', '.join([type(cinema_chain).__name__ for cinema_chain in all_cinema_chains])
        print(f'The installed chains are: {installed_chains}')


@cli.command('run')
@click.option('--chain', default=None, show_default=True, type=click.STRING, help='The archiver class name to run')
@click.option('--dry-run', 'dry_run', is_flag=True, default=False, show_default=False, type=click.BOOL, help='Run, but don\'t make any changes to the DB')
def run_cmd(chain: Optional[str], dry_run: bool) -> None:
    """Runs the archiver on all cinema chains"""
    if dry_run:
        print('Dry run, no changes to DB')
    if chain is None:
        run_all(dry_run)
    else:
        installed_chains = [type(cinema_chain).__name__ for cinema_chain in all_cinema_chains]
        if chain not in installed_chains:
            raise click.BadOptionUsage('--chain', f'No such installed chain "{chain}"')
        run_single(chain, dry_run)


if __name__ == '__main__':
    cli()
