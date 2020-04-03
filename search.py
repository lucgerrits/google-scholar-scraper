#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraping documentation on Google Scholar.

@author: Luc Gerrits
"""
from langid.langid import langid
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
import zipfile
import socket
print(__doc__)


############################
#     global config
############################
query = ""  # 'EOSIO "EOS.IO"'  # filetype:pdf
limit = 10
files_folder = "./files/"
csv_file_name = files_folder + 'results.csv'
showbrowser = False  # True
verbose = False
geckodriver_path = "./geckodriver"
languages = ["en", "fr"]
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

linkHistory = []
filters = []  # domains to skip

verboseprint = print if verbose else lambda *a, **k: None


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_connected():
    #https://stackoverflow.com/a/20913928/13187605
    try:
        # see if we can resolve the host name -- tells us if there is
        # a DNS listening
        host = socket.gethostbyname("1.1.1.1")
        # connect to the host -- tells us if the host is actually
        # reachable
        s = socket.create_connection((host, 80), 2)
        s.close()
        return True
    except:
        pass
    return False


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


def findElementsXpath(root_element, xpath):
    try:
        element = root_element.find_elements_by_xpath(xpath)
        return element
    except NoSuchElementException:
        print("NoSuchElementException: (xpath) {}".format(xpath))
        return ""


def getPage(driver, url):
    try:
        driver.get(url)
        return True
    except InvalidArgumentException:
        print("InvalidArgumentException: {}".format(url))
        return False
    except TimeoutException:
        print("TimeoutException: {}".format(url))
        return False


def make_request(url):
    try:
        response = requests.get(url)
        return response
    except requests.exceptions.RequestException as err:
        print("\nCan't get PDF", err)

    return -1


def validate_field(field):
    if not field:
        field = 'N/A'
    return field


def string_to_filename(title):
    return title.replace("/", "_").replace(" ", "_")


def handleData(element, writer, try_download_pdf):
    print("{} | Found: {}".format(now(), element["title"]))
    lang_detected = langid.classify(element["title"])
    if lang_detected[0] not in languages:
        print("{} | '{}' is not in required languages ({})".format(
            now(), lang_detected[0], ', '.join(languages)))
        return
    has_pdf = "no"
    if try_download_pdf:
        try:
            response = make_request(element["url"])
            if response != -1:
                content_type = response.headers['content-type']
                extension = mimetypes.guess_extension(content_type)
                if extension == ".pdf":
                    if element["title"] != "":
                        tmp_filename = "{}{}-{}.pdf".format(
                            files_folder, string_to_filename(now()), string_to_filename(element["title"]))
                    else:
                        tmp_filename = "{}{}-{}.pdf".format(
                            files_folder, string_to_filename(now()), "no_title")
                    tmp = open(tmp_filename, 'wb')
                    tmp.write(response.content)
                    tmp.close()
                    print("{} | Downloaded PDF".format(now()))
                    has_pdf = "yes"
        except KeyError:
            pass
    writer.writerow([validate_field(element["title"]),
                     validate_field(has_pdf),
                     validate_field(element["date"]),
                     now(),
                     validate_field(element["authors"]),
                     validate_field(element["url"])
                     ])


def handleLink(element, writer, try_download_pdf):
    if isLinkInHistory(element["url"]):
        return
    else:
        handleData(element, writer, try_download_pdf)


def searchGoogleScholar(driver, writer, page, nb_elements):
    if page == 0:
        q = {'q': query}
    else:
        q = {'q': query, 'start': int(page*10)}
    url = 'https://scholar.google.com/scholar?hl=en&scisbd=2&as_sdt=1%2C5&as_vis=1&{}'.format(
        urllib.parse.urlencode(q))
    if not getPage(driver, url):
        print("Failed to get google scholar web page.")
        return 0

    main_results = findElementsXpath(driver, "//*[@class='gs_r gs_or gs_scl']")
    i = 0
    for elem in main_results:
        a_tag = findElementsXpath(elem, ".//a[@href and @data-clk]")
        date = findElementsXpath(elem, ".//*[@class='gs_age']")
        authors = findElementsXpath(elem, ".//*[@class='gs_a']")
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
        if limit > nb_elements:
            handleLink(data, writer, try_download_pdf)
            nb_elements += 1
            i += 1
        else:
            return i
    return i


def _search():
    csv_file = open(csv_file_name, 'w', encoding='utf-8')
    writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
    writer.writerow(['Title', "Has PDF", "Date",
                     "Timestamp", 'Authors', 'URL'])
    driver = webdriver.Firefox(
        executable_path=geckodriver_path, options=options)
    driver.set_page_load_timeout(60)
    print("{} | Limit is set to {} results.".format(now(), limit))
    # init
    print("{} | Init google".format(now()))
    getPage(driver, 'https://www.google.com/')
    time.sleep(randTime())
    # start
    nb_elements = 0
    for curr_page in range(0, nb_page):
        print("{} | Crawling page n°{}".format(now(), curr_page+1))
        nb_elements += searchGoogleScholar(driver,
                                           writer, curr_page, nb_elements)
        time.sleep(randTime())
    # end
    print("{} | Found {} elements".format(now(), nb_elements))
    end = time.time()
    elapsed = end - start
    print("{} | Elapsed time: {}".format(
        now(), time.strftime("%H:%M:%S", time.gmtime(elapsed))))
    driver.close()
    csv_file.close()


def zipdir(path, ziph):
    # Source: https://stackoverflow.com/a/1855118
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".pdf") or file.endswith(".csv"):
                ziph.write(os.path.join(root, file))


def _compress():
    zip_filename = string_to_filename('{}_q={}.zip'.format(
        now(), query))
    zipf = zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED)
    zipdir(files_folder, zipf)
    zipf.close()
    print("{} | Saved in: {}".format(now(), zip_filename))


def _clear_files():
    dir_name = files_folder
    test = os.listdir(dir_name)
    for item in test:
        if item.endswith(".pdf") or item.endswith(".csv"):
            os.remove(os.path.join(dir_name, item))


def main():
    if not is_connected():
        print("Not internet connection.")
        sys.exit(1)
    _clear_files()
    if len(sys.argv) > 1:
        if sys.argv[1] == "reset":
            print("{} | Just remove all temporay files.".format(now()))
            sys.exit(0)
    _search()
    _compress()
    _clear_files()


main()
