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


bbc_url = "https://www.bbc.co.uk/programmes/formats/films/player"

with open("omdb_api_key.txt") as omdb_api_key:
    api_key = omdb_api_key.read().strip()


def extract_film_info(film):
    title = film.select_one(".programme__title").text

    r = requests.get("http://www.omdbapi.com/?t={}&apikey={}".format(
        title,
        api_key
    ))

    info = {
        "bbc": {
            "html": str(film),
            "id": film['data-pid'],
        },
        "title": title,
        "omdb": r.json(),

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
        output_f.write(pystache.render(template, {"films": films_sorted}))


def main():
    film_details = []

    films_page = requests.get(bbc_url)

    soup = BeautifulSoup(films_page.text, "html.parser")

    films = soup.find_all("div", class_="programme")

    for film in films:
        film_details.append(extract_film_info(film))

    with open("films.json", "w") as json_out:
        json_out.write(json.dumps(film_details, indent=2))

    render_html(film_details)


if __name__ == "__main__":
    main()
