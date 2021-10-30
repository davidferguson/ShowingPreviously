from setuptools import find_packages, setup

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name = 'showingpreviously',
    version = '0.2.2',
    description = 'An archiver of cinema movie showtimes',
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    url = '',
    extras_require = dict(tests=['pytest']),
    packages = find_packages(where='src'),
    package_dir = {'': 'src'},
    entry_points = {
        'console_scripts': ['showingpreviously=showingpreviously.cli:cli']
    },
    install_requires = [
        'click',
        'appdirs',
        'pytz',
        'requests',
        'beautifulsoup4',
    ],
)
