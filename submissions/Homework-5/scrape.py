#!/usr/bin/python
# -*- coding: utf-8 -*-

# Adlai Gordon

import os
import sys
import time
import argparse
import logging
import requests
from BeautifulSoup import BeautifulSoup


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
loghandler = logging.StreamHandler(sys.stderr)
loghandler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
log.addHandler(loghandler)

base_url = "http://www.tripadvisor.com/"
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.76 Safari/537.36"

def debug(debug_str):
    with open('debug.txt', "a") as debug_log:
      debug_log.write("{}\n\n".format(debug_str))

def get_city_page(city, state, datadir):
    """ Returns the URL of the list of the hotels in a city. Corresponds to
    STEP 1 & 2 of the slides.

    Parameters
    ----------
    city : str

    state : str

    datadir : str


    Returns
    -------
    url : str
        The relative link to the website with the hotels list.

    """
    # Build the request URL
    url = base_url + "city=" + city + "&state=" + state
    # Request the HTML page
    headers = {'User-Agent': user_agent}
    response = requests.get(url, headers=headers)
    html = response.text.encode('utf-8')
    with open(os.path.join(datadir, city + '-tourism-page.html'), "w") as h:
        h.write(html)

    # Use BeautifulSoup to extract the url for the list of hotels in
    # the city and state we are interested in.

    # For example in this case we need to get the following href
    # <li class="hotels twoLines">
    # <a href="/Hotels-g60745-Boston_Massachusetts-Hotels.html" data-trk="hotels_nav">...</a>
    soup = BeautifulSoup(html)
    li = soup.find("li", {"class": "hotels twoLines"})
    city_url = li.find('a', href=True)
    return city_url['href']


def get_hotellist_page(city_url, page_count, city, datadir='data/'):
    """ Returns the hotel list HTML. The URL of the list is the result of
    get_city_page(). Also, saves a copy of the HTML to the disk. Corresponds to
    STEP 3 of the slides.

    Parameters
    ----------
    city_url : str
        The relative URL of the hotels in the city we are interested in.
    page_count : int
        The page that we want to fetch. Used for keeping track of our progress.
    city : str
        The name of the city that we are interested in.
    datadir : str, default is 'data/'
        The directory in which to save the downloaded html.

    Returns
    -------
    html : str
        The HTML of the page with the list of the hotels.
    """
    url = base_url + city_url
    # Sleep 2 sec before starting a new http request
    time.sleep(2)
    # Request page
    headers = { 'User-Agent' : user_agent }
    response = requests.get(url, headers=headers)
    html = response.text.encode('utf-8')
    # Save the webpage
    with open(os.path.join(datadir, city + '-hotellist-' + str(page_count) + '.html'), "w") as h:
        h.write(html)
    return html


def parse_hotellist_page(html, page_count, city, datadir='data/'):
    """Parses the website with the hotel list and prints the hotel name, the
    number of stars and the number of reviews it has. If there is a next page
    in the hotel list, it returns a list to that page. Otherwise, it exits the
    script. Corresponds to STEP 4 of the slides.

    Parameters
    ----------
    html : str
        The HTML of the website with the hotel list.

    Returns
    -------
    URL : str
        If there is a next page, return a relative link to this page.
        Otherwise, exit the script.
    """
    soup = BeautifulSoup(html)
    # Extract hotel name, star rating and number of reviews
    hotel_boxes = soup.findAll('div', {'class' :'listing wrap reasoning_v5_wrap jfy_listing p13n_imperfect'})
    if not hotel_boxes:
        log.info("#################################### Option 2 ######################################")
        hotel_boxes = soup.findAll('div', {'class' :'listing_info jfy'})
    if not hotel_boxes:
        log.info("#################################### Option 3 ######################################")
        hotel_boxes = soup.findAll('div', {'class' :'listing easyClear  p13n_imperfect'})

    i = 0
    for hotel_box in hotel_boxes:

        hotel_link = hotel_box.find("a", {"target" : "_blank"})
        hotel_name = hotel_link.find(text=True).strip()

        url = base_url + hotel_link['href']
        time.sleep(2)
        # Request page
        headers = { 'User-Agent' : user_agent }
        response = requests.get(url, headers=headers)
        html = response.text.encode('utf-8')
        # Save the webpage

        # file_name = "{}-hotel-{}.html".format(city, hotel_name.lower().replace (" ", "_"))
        # with open(os.path.join(datadir, file_name), "w") as h:
        #     h.write(html)
        parse_hotel_page(city, hotel_name, html, datadir)
        i += 1      
        
    # Get next URL page if exists, otherwise exit
    # div = soup.find("div", {"class" : "unified pagination "})
    div = soup.find("div", {"class": "pagination paginationfillbtm"})
    # check if this is the last page
    # if div.find('span', {'class' : 'nav next disabled'}):
    if div.find('span', {'class' : 'guiArw pageEndNext'}):
        log.info("We reached last page")
        return None
    # If not, return the url to the next page
    hrefs = div.findAll('a', href= True)
    
    for href in hrefs:
        if href.find(text = True) == '&raquo;':
            log.info("Next url is %s" % href['href'])
            return href['href']

def parse_hotel_page(city, hotel_name, html = None, datadir='data/'):
    log.info("Parsing %s" % hotel_name)
    # debug("Parsing %s" % hotel_name)

    info = {}
    ratings = [0] * 6

    soup = BeautifulSoup(html)
    form = soup.find("form", {"id": "REVIEW_FILTER_FORM"})

    # Ratings
    ul = form.find("ul", {"class": "barChart"})
    i = 5
    for r in ul.findAll("div", {"class": "wrap row"}):
        text = r.find("span", {"class":"text"}).findAll(text=True)[0].strip().replace(" ", "_")
        num = int(str(r.find("span", {"class":"compositeCount"}).findAll(text=True)[0].replace(",", "")))
        ratings[i] = num
        info[text] = num
        i -= 1

    avg_score = 1.0 * sum([i * ratings[i] for i in range(len(ratings))]) / sum(ratings)
    info["avg_score"] = avg_score

    excellent = ratings[5] > (.6 * sum(ratings))
    info["is_excellent"] = excellent

    reviewer_type = ["Familes", "Couples", "Solo", "Business"]
    for i in range(len(reviewer_type)):
        segment = "segment segment" + str(i + 1)
        info[reviewer_type[i]] = int(str(form.find("div", {"class": segment}).find("div", {"class":"value"}).findAll(text = True)[0].replace(",", "")))    

    spans = soup.find("div", {"id": "SUMMARYBOX"}).findAll("span", {"class":"rate sprite-rating_s rating_s"})
    summary_types = ["Location", "Sleep_Quality", "Rooms", "Service", "Value", "Cleanliness"]
    summary_ratings = [float(span.find("img")['alt'].split()[0]) for span in spans]
    for i in range(len(summary_types)):
        info[summary_types[i]] = summary_ratings[i]


    debug(info)
    # return info
    hotel_info[hotel_name] = info
    with open('hotel_info.txt', "w") as hotel_info_log:
      hotel_info_log.write("{}".format(hotel_info))

hotel_info = {}

def scrape_hotels(city, state, datadir='data/'):
    """Runs the main scraper code

    Parameters
    ----------
    city : str
        The name of the city for which to scrape hotels.

    state : str
        The state in which the city is located.

    datadir : str, default is 'data/'
        The directory under which to save the downloaded html.
    """
    global hotel_info
    hotel_info = {}
    # Get current directory
    current_dir = os.getcwd()
    # Create datadir if does not exist
    if not os.path.exists(os.path.join(current_dir, datadir)):
        os.makedirs(os.path.join(current_dir, datadir))

    # Get URL to obtaint the list of hotels in a specific city
    city_url = get_city_page(city, state, datadir)
    c = 0
    while(True):
        c += 1
        html = get_hotellist_page(city_url, c, city, datadir)
        city_url = parse_hotellist_page(html, c, city, datadir)
        if city_url == None:
            break

    return hotel_info

'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape tripadvisor')
    parser.add_argument('-datadir', type=str,
                        help='Directory to store raw html files',
                        default="data/")
    parser.add_argument('-state', type=str,
                        help='State for which the hotel data is required.',
                        required=True)
    parser.add_argument('-city', type=str,
                        help='City for which the hotel data is required.',
                        required=True)

    args = parser.parse_args()
    scrape_hotels(args.city.lower(), args.state.lower(), args.datadir)


'''


