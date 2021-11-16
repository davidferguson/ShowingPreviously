from selenium import webdriver, common
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver

from typing import Optional


WEBDRIVER: Optional[WebDriver] = None


def get_selenium_webdriver() -> WebDriver:
    global WEBDRIVER
    if WEBDRIVER is None:
        try:
            chrome_options = ChromeOptions()
            # running headless will stop cloudflare from working
            # chrome_options.headless = True
            WEBDRIVER = webdriver.Chrome(options=chrome_options)
        except common.exceptions.WebDriverException:
            firefox_options = FirefoxOptions()
            # running headless will stop cloudflare from working
            # firefox_options.headless = True
            WEBDRIVER = webdriver.Firefox(options=firefox_options)
    return WEBDRIVER


def close_selenium_webdriver() -> None:
    global WEBDRIVER
    if WEBDRIVER is not None:
        WEBDRIVER.close()
