#!/usr/bin/env python3
import argparse
import csv
import json
import os
import urllib.parse

import requests

API_BASE = "https://www.broadbandmap.gov/broadbandmap/"

DATA_DIR = "data"
DISTRICTS_FILENAME = "districts.json"
PROVIDERS_FILENAME_PATTERN = "providers-{}.json"
STATS_FILENAME_PATTERN = "stats-{}-{}.json"
RANKING_PROPERTIES_FILENAME_PATTERN = "ranking-properties-{}.json"
CSV_FILENAME = "summary.csv"

RANKING_PROPERTIES_URL = [
    "wirelineproviderequals0",
    "wirelineprovidergreaterthan1",
    "wirelineprovidergreaterthan2",
    "wirelineprovidergreaterthan3",
    "wirelineprovidergreaterthan4",
    "wirelineprovidergreaterthan5",
    "wirelineprovidergreaterthan6",
    "wirelineprovidergreaterthan7",
    "wirelineprovidergreaterthan8"
]
RANKING_PROPERTIES_JSON = [
    "wirelineProviderEquals0",
    "wirelineProviderGreaterThan1",
    "wirelineProviderGreaterThan2",
    "wirelineProviderGreaterThan3",
    "wirelineProviderGreaterThan4",
    "wirelineProviderGreaterThan5",
    "wirelineProviderGreaterThan6",
    "wirelineProviderGreaterThan7",
    "wirelineProviderGreaterThan8"
]


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
        raise Exception("Downloading provider list failed: {}"
                        .format(response_object.get("message")))


def parse_providers_list(file_path):
    with open(file_path) as f:
        return json.load(f)["allProviders"]


def download_provider_stats(dataVersion, state_id, district_id, provider_id,
                            file_path):
    url = urllib.parse.urljoin(API_BASE, "provider/{}/stats/state/{}/"
                                         "population/congdistrict/{}/{}"
                                         "?format=json"
                                         .format(dataVersion, state_id,
                                                 district_id, provider_id))
    resp = requests.get(url)
    response_object = resp.json()
    if response_object.get("status") == "OK":
        results = response_object["Results"]
        with open(file_path, "w") as f:
            json.dump(results, f)
    else:
        raise Exception("Downloading provider statistics failed: {}"
                        .format(response_object.get("message")))


def download_ranking_properties(dataVersion, data_version_dir, state_id,
                                district_id, state_abbreviation_lookup):
    properties = ",".join(RANKING_PROPERTIES_URL)
    url = urllib.parse.urljoin(API_BASE, "almanac/{}/rankby/state/{}/"
                                         "population/"
                                         "wirelineprovidergreaterthan1/"
                                         "congdistrict/id/{}"
                                         "?format=json&order=asc"
                                         "&properties={}"
                                         .format(dataVersion, state_id,
                                                 district_id, properties))
    resp = requests.get(url)
    response_object = resp.json()
    if response_object.get("status") == "OK":
        results = response_object["Results"]
        for result_list in (results["FirstTen"], results["myArea"],
                            results["LastTen"], results["All"]):
            for district in result_list:
                district_number = district["geographyName"]
                state_id = district["stateFips"]
                state_abbr = state_abbreviation_lookup[state_id]
                district_name = "{}-{}".format(state_abbr, district_number)
                ranking_properties_path = os.path.join(
                    data_version_dir,
                    RANKING_PROPERTIES_FILENAME_PATTERN.format(district_name)
                )
                if not os.path.isfile(ranking_properties_path):
                    with open(ranking_properties_path, "w") as f:
                        json.dump(district, f)
    else:
        raise Exception("Downloading provider statistics failed: {}"
                        .format(response_object.get("message")))


def district_sort_key(district):
    return district["stateAbbreviation"], district["geographyName"]


def generate_csv(data_version_dir):
    with open(os.path.join(data_version_dir, CSV_FILENAME), "w") as csv_file:
        fieldnames = ["District"] + RANKING_PROPERTIES_JSON
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        districts_path = os.path.join(data_version_dir, DISTRICTS_FILENAME)
        districts = parse_districts(districts_path)
        for district in sorted(districts, key=district_sort_key):
            state_abbr = district["stateAbbreviation"]
            district_number = district["geographyName"]
            district_name = "{}-{}".format(state_abbr, district_number)
            ranking_properties_path = os.path.join(
                data_version_dir,
                RANKING_PROPERTIES_FILENAME_PATTERN.format(district_name)
            )
            with open(ranking_properties_path) as json_file:
                properties = json.load(json_file)
                row_dict = {field: properties[field]
                            for field in RANKING_PROPERTIES_JSON}
                row_dict["District"] = district_name
                writer.writerow(row_dict)


def main():
    parser = argparse.ArgumentParser(description="Download broadband map data")
    parser.add_argument("--dataVersion", metavar="monYEAR", default="jun2014")
    parser.add_argument("--providerStatistics", action="store_true")
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

    state_abbreviation_lookup = {}
    for district in districts:
        state_id = district["stateFips"]
        state_abbr = district["stateAbbreviation"]
        state_abbreviation_lookup[state_id] = state_abbr

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

        if args.providerStatistics:
            providers = parse_providers_list(providers_path)
            for provider in providers:
                provider_id = provider["holdingCompanyNumber"]

                stats_path = os.path.join(data_version_dir,
                                          STATS_FILENAME_PATTERN
                                          .format(district_name, provider_id))

                if not os.path.isfile(stats_path):
                    download_provider_stats(args.dataVersion, state_id,
                                            district_id, provider_id,
                                            stats_path)

        ranking_properties_path = os.path.join(
            data_version_dir,
            RANKING_PROPERTIES_FILENAME_PATTERN.format(district_name)
        )
        if not os.path.isfile(ranking_properties_path):
            download_ranking_properties(args.dataVersion, data_version_dir,
                                        state_id, district_id,
                                        state_abbreviation_lookup)
            if not os.path.isfile(ranking_properties_path):
                raise Exception("Failed to download ranking properties for {}"
                                .format(district_name))

    generate_csv(data_version_dir)


if __name__ == "__main__":
    main()
