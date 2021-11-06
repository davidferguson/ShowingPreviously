from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

from typing import Optional


WEBDRIVER: Optional[WebDriver] = None


def get_selenium_webdriver() -> WebDriver:
    global WEBDRIVER
    if WEBDRIVER is None:
        WEBDRIVER = webdriver.Chrome()
    return WEBDRIVER


def close_selenium_webdriver() -> None:
    global WEBDRIVER
    if WEBDRIVER is not None:
        WEBDRIVER.close()
