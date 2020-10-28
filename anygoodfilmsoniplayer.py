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


bbc_url = "https://www.bbc.co.uk/programmes/formats/films/player"

with open("omdb_api_key.txt") as omdb_api_key:
    api_key = omdb_api_key.read().strip()


def extract_film_info(film):
    title = film.select_one(".programme__title").text

    omdbapi_url = "http://www.omdbapi.com/"

    r = requests.get(omdbapi_url, params={"t": title, "apikey": api_key})

    omdb_info = r.json()

    # Internal object for easier sorting
    _ratings = []

    # We might not find omdb_info for this film
    try:
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
    except KeyError:
        pass

    info = {
        "bbc": {
            "html": str(film),
            "id": film['data-pid'],
        },
        "title": title,
        "omdb": omdb_info,
        "_ratings": _ratings,
    }

    # Avoid hitting omdbapi too hard
    time.sleep(2)

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


def main():
    film_details = []

    parser = argparse.ArgumentParser()

    parser.add_argument("--from-file",
                        help="Use json file input to generate output """
                        """instead of from the web""")

    args = parser.parse_args()

    if args.from_file:
        # Fetch films from file
        with open(args.from_file, "r") as f:
            film_details = json.load(f)
    else:
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
                film_details.append(extract_film_info(film))

            page = page + 1

        with open("films.json", "w") as json_out:
            json_out.write(json.dumps(film_details, indent=2))

    render_html(film_details)


if __name__ == "__main__":
    main()
