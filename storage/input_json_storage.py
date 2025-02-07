# input_json_storage.py
# Description: Central module for working with JSON-based storage.


import os
import json
import click
from typing import List, Dict
from user_input_parser import PolynomialParser
from apn_object import APN

STORAGE_DIR = "storage"
INPUT_APNS_FILE = os.path.join(STORAGE_DIR, "input_apns.json")

def ensure_storage_folder():
    if not os.path.isdir(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)

def load_input_apns() -> List[APN]:
    # Reads APNs from input_apns.json and returns them as a list of APN objects.
    ensure_storage_folder()
    if not os.path.isfile(INPUT_APNS_FILE):
        return []

    with open(INPUT_APNS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    parser = PolynomialParser()
    apn_list = []
    for apn_data in data:
        try:
            apn = parser.parse_univariate_polynomial(
                apn_data["poly"],
                apn_data["field_n"],
                apn_data["irr_poly"]
            )
            apn.properties = apn_data.get("properties", {})
            apn.invariants = apn_data.get("invariants", {})
            apn_list.append(apn)
        except Exception as e:
            click.echo(f"Error loading APN from file: {e}", err=True)

    return apn_list

def save_input_apns(apn_list: List[APN]) -> None:
    # Writes the list of APN objects to input_apns.json.
    ensure_storage_folder()
    data = []
    for apn in apn_list:
        apn_data = {
            "field_n": apn.field_n,
            "irr_poly": apn.irr_poly,
            "poly": apn.representation.univariate_polynomial,
            "properties": apn.properties,
            "invariants": apn.invariants
        }
        data.append(apn_data)

    with open(INPUT_APNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    click.echo(f"Saved {len(apn_list)} input APNs to {INPUT_APNS_FILE}.")