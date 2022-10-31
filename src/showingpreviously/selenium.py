from selenium import webdriver, common
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver

from typing import Optional

from showingpreviously.consts import WEBDRIVER_ORDER
from showingpreviously.model import CinemaArchiverException


WEBDRIVER: Optional[WebDriver] = None


def get_selenium_webdriver() -> WebDriver:
    global WEBDRIVER
    if WEBDRIVER is None:
        for i, webdriver_name in enumerate(WEBDRIVER_ORDER):
            try:
                WEBDRIVER = get_specific_webdriver(webdriver_name)
                return WEBDRIVER
            except common.exceptions.WebDriverException as e:
                pass
        raise CinemaArchiverException("No available webdriver found")


def get_specific_webdriver(webdriver_name: str) -> WebDriver:
    if webdriver_name == 'Firefox':
        firefox_options = FirefoxOptions()
        # running headless will stop cloudflare from working
        # firefox_options.headless = True
        return webdriver.Firefox(options=firefox_options)
    elif webdriver_name == 'Chrome':
        chrome_options = ChromeOptions()
        # running headless will stop cloudflare from working
        # chrome_options.headless = True
        return webdriver.Chrome(options=chrome_options)
    else:
        raise CinemaArchiverException(f'Unknown webdriver name: {webdriver_name}')


def close_selenium_webdriver() -> None:
    global WEBDRIVER
    if WEBDRIVER is not None:
        WEBDRIVER.close()
