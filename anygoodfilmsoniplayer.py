#!/usr/bin/env python3
#
# Copyright Michael Wood 2020
# MichaelWood.me.uk
# AGPL

# OMDB api https://www.omdbapi.com/

from bs4 import BeautifulSoup

import requests
import time
import json
import pystache
import datetime
import argparse
import re


bbc_url = "https://www.bbc.co.uk/programmes/formats/films/player"
channelfour_url = "https://www.channel4.com/categories/film?json=true"

with open("omdb_api_key.txt") as omdb_api_key:
    api_key = omdb_api_key.read().strip()


def create_film_info(film_title, film_year=None):
    class TitleMissMatchError(Exception):
        pass

    omdbapi_url = "http://www.omdbapi.com/"

    r = requests.get(omdbapi_url, params={"t": film_title, "apikey": api_key,
                                          "y": film_year, "type": "movie"})
    print(r.url)

    omdb_info = r.json()

    # Internal object for easier sorting
    _ratings = []

    # We might not find omdb_info for this film
    try:
        if film_title.lower() != omdb_info['Title'].lower():
            print("film titles don't match %s to %s" % (film_title,
                                                        omdb_info['Title']))
            # Simulate the response false
            omdb_info = {"Response": False}
            raise TitleMissMatchError
        for rating in omdb_info['Ratings']:
            val = 0
            _rating = {}
            _rating['source'] = rating['Source'].lower().replace(" ", "_")

            # Parse the values
            if "internet" in _rating['source'] or \
               "metacritic" in _rating["source"]:
                val = float(rating['Value'].split("/")[0])

            if "rotten" in _rating['source']:
                val = int(rating['Value'].split("%")[0])

            _rating['value'] = val

            _ratings.append(_rating)
    except (KeyError, TitleMissMatchError):
        pass

    info = {
        "title": film_title,
        "omdb": omdb_info,
        "_ratings": _ratings,
    }

    # Avoid hitting omdbapi too hard
    time.sleep(1)

    return info


def get_rating(film):
    try:
        return float(film['omdb']['imdbRating'])
    except (KeyError, ValueError):
        return 0


def render_html(films):
    films_sorted = sorted(films, key=get_rating, reverse=True)

    with open("template.html") as template_f:
        template = template_f.read()

    with open("index.html", "w") as output_f:
        output_f.write(pystache.render(
            template,
            {"films": films_sorted,
             "updated": datetime.datetime.now().strftime("%c")}
        ))


def bbc_films():
    bbc_films = []

    # Fetch films from the bbc interwebs
    # Start at page 1 of the films page
    page = 1
    while True:
        if page == 1:
            films_page = requests.get(bbc_url)
        else:
            films_page = requests.get(bbc_url, params={"page": page})

            soup = BeautifulSoup(films_page.text, "html.parser")

            if "Sorry, that page was not found" in soup.title.string:
                break

            if page > 100:
                print("Emergency break applied")
                break

            films = soup.find_all("div", class_="programme")

            for film in films:
                film_title = film.select_one(".programme__title").text

                film_info = create_film_info(film_title)
                # Add BBC specific info
                film_info['provider'] = 'BBC'

                film_info['href'] = \
                    "https://www.bbc.co.uk/iplayer/episode/{}".format(
                        film['data-pid'])

                film_info['raw'] = {"html": str(film)}

                bbc_films.append(film_info)

        page = page + 1

    return bbc_films


def channelfour_films():
    films = []
    offset = 0

    # Regex matches value inside (yyyy) e.g. from overlayText
    # "(2017) Survival drama. A trip goes horribly wrong for an"
    year_regex = re.compile(r'(?<=\()\d{4}(?=\))')

    while True:
        films_data = requests.get(channelfour_url, params={"json": "true",
                                                           "offset":
                                                           offset}).json()

        items_in_page = len(films_data['brands']['items'])

        if items_in_page == 0:
            break

        if offset > 500:
            print("Emergency break applied")
            break

        for film in films_data['brands']['items']:
            year = None
            year_search = year_regex.search(film['overlayText'])
            if year_search:
                year = year_search.group(0)

            film_info = create_film_info(film['labelText'], year)

            # Add Channel4 specific info
            film_info['provider'] = "Channel4"
            film_info['href'] = film['hrefLink']
            film_info['raw'] = film
            films.append(film_info)

        offset += items_in_page

    return films


def main():
    films = []

    parser = argparse.ArgumentParser()

    parser.add_argument("--from-file",
                        help="Use json file input to generate output """
                        """instead of from the web""")

    args = parser.parse_args()

    if args.from_file:
        # Fetch films from file
        with open(args.from_file, "r") as f:
            films = json.load(f)
    else:
        films += bbc_films()
        films += channelfour_films()

        with open("films.json", "w") as json_out:
            json_out.write(json.dumps(films, indent=2))

    render_html(films)


if __name__ == "__main__":
    main()
