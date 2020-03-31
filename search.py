#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraping documentation on Google Scholar.

@author: Luc Gerrits
"""
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import InvalidArgumentException
from selenium.common.exceptions import NoSuchElementException
# from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
import urllib
import csv
import random
import datetime
import requests
import mimetypes
import time
import os
import sys
print(__doc__)


############################
#     global config
############################
query = ""  # 'EOSIO "EOS.IO"'  # filetype:pdf
limit = 10
file_name = 'results.csv'
showbrowser = False  # True
verbose = False
pdf_folder = "./files/"
geckodriver_path = "./geckodriver"
############################

if len(sys.argv) < 2:
    print("Please enter query, examples:\n {} 'EOSIO'".format(sys.argv[0]))
    print(" {} 'EOSIO \"EOS.IO\"'".format(sys.argv[0]))
    print(" {} 'EOSIO \"EOS.IO\" filetype:pdf'".format(sys.argv[0]))
    sys.exit(1)
else:
    query = sys.argv[1]

if len(sys.argv) > 2:
    limit = int(sys.argv[2])

if not os.path.isfile(geckodriver_path):
    print("Cannot find selenium driver: {}".format(geckodriver_path))
    sys.exit(1)
start = time.time()
nb_page = int(limit//10) if int(limit//10) > 0 else 1
# selenium driver and options
options = Options()
if not showbrowser:
    options.add_argument("--headless")
driver = webdriver.Firefox(executable_path=geckodriver_path, options=options)
driver.set_page_load_timeout(15)

csv_file = open(file_name, 'w', encoding='utf-8')
writer = csv.writer(csv_file)
writer.writerow(['Title', "Date", "Timestamp", 'Authors', 'URL'])

linkHistory = []
filters = []  # domains to skip

verboseprint = print if verbose else lambda *a, **k: None

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def isLinkInHistory(url):
    for element in filters:
        if element in url:
            verboseprint("Skip ", url, "Filter")
            return True
    if not url in linkHistory:
        verboseprint("Go ", url)
        linkHistory.append(url)
        return False
    else:
        verboseprint("Skip ", url)
        return True


def randTime():
    return random.randint(1, 2) + round(random.random(), 2)


def findElementXpath(xpath):
    try:
        element = driver.find_element_by_xpath(xpath)
        return element
    except NoSuchElementException:
        print("NoSuchElementException: (xpath) {}".format(xpath))
        return ""


def getPage(url):
    try:
        driver.get(url)
        return True
    except InvalidArgumentException:
        print("InvalidArgumentException: {}".format(url))
        return False
    except TimeoutException:
        print("TimeoutException: {}".format(url))
        return False


def validate_field(field):
    if not field:
        field = 'N/A'
    return field


def handleData(element, try_download_pdf):
    print("{} | ".format(now()), end="")
    print(element["title"], end="")
    writer.writerow([validate_field(element["title"]),
                     validate_field(element["date"]),
                     now(),
                     validate_field(element["authors"]),
                     validate_field(element["url"])
                     ])
    if try_download_pdf:
        try:
            response = requests.get(element["url"])
            content_type = response.headers['content-type']
            extension = mimetypes.guess_extension(content_type)
            if extension == ".pdf":
                if element["title"] != "":
                    tmp_filename = pdf_folder + \
                        element["title"].replace(
                            " ", "_").replace("/", "_") + ".pdf"
                else:
                    tmp_filename = pdf_folder + now() + ".pdf"
                tmp = open(tmp_filename, 'wb')
                tmp.write(response.content)
                tmp.close()
                print(" | PDF")
        except KeyError:
            return
    else:
        print("")


def handleLink(element, try_download_pdf):
    if isLinkInHistory(element["url"]):
        return
    else:
        handleData(element, try_download_pdf)


def searchGoogleScholar(page):
    if page == 0:
        q = {'q': query}
    else:
        q = {'q': query, 'start': int(page*10)}
    url = 'https://scholar.google.com/scholar?hl=en&scisbd=2&as_sdt=1%2C5&as_vis=1&{}'.format(
        urllib.parse.urlencode(q))
    if not getPage(url):
        return

    main_results = driver.find_elements_by_xpath(
        "//*[@class='gs_r gs_or gs_scl']")
    i = 0
    for elem in main_results:
        a_tag = elem.find_elements_by_xpath(".//a[@href and @data-clk]")
        date = elem.find_elements_by_xpath(".//*[@class='gs_age']")
        authors = elem.find_elements_by_xpath(".//*[@class='gs_a']")
        try_download_pdf = False
        try:
            if "span" in a_tag[0].get_attribute('innerHTML'):
                title = a_tag[1].text  # use second title
                if "PDF" in a_tag[0].text:
                    try_download_pdf = True
            else:
                title = a_tag[0].text
        except IndexError:
            title = ""
        try:
            url = a_tag[0].get_attribute("href")
        except IndexError:
            url = ""
        try:
            authors = authors[0].text
        except IndexError:
            authors = ""
        try:
            date = date[0].text
        except IndexError:
            date = ""
        data = {
            "title": title,
            "url": url,
            "authors": authors,
            "date": date
        }
        handleLink(data, try_download_pdf)
        i += 1
    return i


def main():
    print("{} | Limit is set to {} results.".format(now(), nb_page*10))
    # init
    print("{} | Init google".format(now()))
    getPage('https://www.google.com/')
    time.sleep(randTime())
    # start
    nb_elements = 0
    for curr_page in range(0, nb_page):
        print("{} | Crawling page {}".format(now(), curr_page))
        nb_elements += searchGoogleScholar(curr_page)
        time.sleep(randTime())
    # end
    print("{} | Found {} elements".format(now(), nb_elements))
    end = time.time()
    elapsed = end - start
    print("{} | Elapsed time: {}".format(now(), time.strftime("%H:%M:%S", time.gmtime(elapsed))))


main()
csv_file.close()
print("{} | Saved in: {}".format(now(), file_name))
driver.close()
