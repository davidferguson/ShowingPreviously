# ShowingPreviously
An archiver of cinema movie showtimes

---

A program to archive showtimes of movies in cinemas, to create a historical record of what movies showed when and where.

## Installation
1. Clone the repo:
   * `git clone https://github.com/davidferguson/ShowingPreviously.git`
   * `cd ShowingPreviously/`
2. Setup a Python3 virtual environment (python3.8+ required):
   * `python3 -m venv venv`
   * `source venv/bin/activate`
3. Install ShowingPreviously:
   * `python setup.py install`
4. Install Chromedriver/Geckodriver:
   * Download Chromedriver/Geckodriver **for the version of Chrome/Firefox you have installed**:
      * Download Geckodriver from https://github.com/mozilla/geckodriver/releases
      * Download Chromedriver from https://chromedriver.chromium.org/downloads
   * Add the downloaded binary to your PATH

## Usage
Installing this module will install the `showingpreviously` command. This has two sub-commands:
1. `showingpreviously info`: Prints info about the program, and basic info about what is stored in the database
2. `showingpreviously run`: Runs the archiver against all cinemas

## Supported Cinemas
- [Cineworld UK](https://www.cineworld.co.uk/) (added 2021-10-31) 
- [Dundee Contemporary Arts Cinema](https://www.dca.org.uk/whats-on/films) (added 2021-10-29)
- [Empire Cinemas](https://www.empirecinemas.co.uk/) (added 2021-11-07)
- [Isle of Bute Discovery Centre Cinema](http://discoverycentrecinema.blogspot.com/) (added 2022-10-30)
- [Odeon](https://odeon.co.uk/) (added 2021-10-31)
- [Omniplex](https://www.omniplex.ie) (added 2021-11-13)
- [Parkway Cinemas](https://parkwaycinemas.co.uk) (added 2021-11-14)
- [Picturehouse](https://www.picturehouses.com/) (added 2021-11-06)
- [The Light Cinemas](https://lightcinemas.co.uk/) (added 2021-10-07)
- [Vue UK](https://www.myvue.com/) (added 2021-10-31)
