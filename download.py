#!/usr/bin/env python3
import argparse
import json
import os
import urllib.parse

import requests

API_BASE = "https://www.broadbandmap.gov/broadbandmap/"

DATA_DIR = "data"
DISTRICTS_FILENAME = "districts.json"
PROVIDERS_FILENAME_PATTERN = "providers-{}.json"


def download_districts(file_path):
    url = urllib.parse.urljoin(API_BASE, "geography/congdistrict"
                                         "?format=json&all=true")
    resp = requests.get(url)
    response_object = resp.json()
    if response_object.get("status") == "OK":
        results = response_object["Results"]
        with open(file_path, "w") as f:
            json.dump(results, f)
    else:
        raise Exception("Downloading congressional districts failed: {}"
                        .format(response_object.get("message")))


def parse_districts(file_path):
    with open(file_path) as f:
        return json.load(f)


def download_provider_list(dataVersion, state_id, district_id, file_path):
    url = urllib.parse.urljoin(API_BASE, "provider/{}/providers/state/{}/"
                                         "population/congdistrict/{}"
                                         "?format=json"
                                         .format(dataVersion, state_id,
                                                 district_id))
    resp = requests.get(url)
    response_object = resp.json()
    if response_object.get("status") == "OK":
        results = response_object["Results"]
        with open(file_path, "w") as f:
            json.dump(results, f)
    else:
        raise Exception("Downloading provider statistics failed: {}"
                        .format(response_object.get("message")))


def parse_providers_list(file_path):
    with open(file_path) as f:
        return json.load(f)["allProviders"]


def main():
    parser = argparse.ArgumentParser(description="Download broadband map data")
    parser.add_argument("--dataVersion", metavar="monYEAR", default="jun2014")
    args = parser.parse_args()

    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)
    data_version_dir = os.path.join(DATA_DIR, args.dataVersion)
    if not os.path.isdir(data_version_dir):
        os.makedirs(data_version_dir)

    districts_path = os.path.join(data_version_dir, DISTRICTS_FILENAME)
    if not os.path.isfile(districts_path):
        download_districts(districts_path)

    districts = parse_districts(districts_path)
    for district in districts:
        state_id = district["stateFips"]
        district_id = district["geographyId"]

        state_abbr = district["stateAbbreviation"]
        district_number = district["geographyName"]
        district_name = "{}-{}".format(state_abbr, district_number)
        providers_path = os.path.join(data_version_dir,
                                      PROVIDERS_FILENAME_PATTERN
                                      .format(district_name))

        if not os.path.isfile(providers_path):
            download_provider_list(args.dataVersion, state_id, district_id,
                                   providers_path)


if __name__ == "__main__":
    main()
