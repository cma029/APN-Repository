# json_storage_utils.py
# Description: Central module for working with JSON-based storage.

import os
import json
import click
from typing import List, Dict
from user_input_parser import PolynomialParser
from apn_object import APN

STORAGE_DIR = "storage"
INPUT_APNS_FILE = os.path.join(STORAGE_DIR, "input_apns.json")
MATCH_LIST_FILE = os.path.join(STORAGE_DIR, "match_list.json")
EQUIV_LIST_FILE = os.path.join(STORAGE_DIR, "equivalence_list.json")

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

def load_match_list() -> Dict[int, List]:
    # Reads the match_list.json file and returns a dict mapping:
    # input_apn_index -> list of (APN, set_of_compare_types).
    ensure_storage_folder()
    if not os.path.isfile(MATCH_LIST_FILE):
        return {}

    with open(MATCH_LIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    parser = PolynomialParser()
    match_list_data = {}
    for apn_idx_str, matches in data.items():
        apn_idx = int(apn_idx_str)
        match_entries = []
        for match_data in matches:
            try:
                apn = parser.parse_univariate_polynomial(
                    match_data["poly"],
                    match_data["field_n"],
                    match_data["irr_poly"]
                )
                apn.properties = match_data.get("properties", {})
                apn.invariants = match_data.get("invariants", {})
                compare_types_list = match_data.get("compare_types", [])
                compare_types_set = set(compare_types_list)
                match_entries.append((apn, compare_types_set))
            except Exception as e:
                click.echo(f"Error loading match APN: {e}", err=True)

        match_list_data[apn_idx] = match_entries

    return match_list_data

def save_match_list(match_list_data: Dict[int, List]) -> None:
    # Writes the match_list dict to match_list.json.
    ensure_storage_folder()
    serializable_list = {}
    for apn_idx, matches in match_list_data.items():
        serializable_matches = []
        for match_apn, comp_types in matches:
            match_data = {
                "field_n": match_apn.field_n,
                "irr_poly": match_apn.irr_poly,
                "poly": match_apn.representation.univariate_polynomial,
                "properties": match_apn.properties,
                "invariants": match_apn.invariants,
                "compare_types": list(comp_types)
            }
            serializable_matches.append(match_data)
        serializable_list[str(apn_idx)] = serializable_matches

    with open(MATCH_LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable_list, f, indent=2)
    click.echo(f"Saved match lists to {MATCH_LIST_FILE}.")

def load_equivalence_list() -> List[dict]:
    # Reads the list of equivalences from equivalence_list.json.
    ensure_storage_folder()
    if not os.path.isfile(EQUIV_LIST_FILE):
        return []
    with open(EQUIV_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_equivalence_list(eq_list: List[dict]) -> None:
    # Writes the list of equivalences to equivalence_list.json.
    ensure_storage_folder()
    with open(EQUIV_LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(eq_list, f, indent=2)
    click.echo(f"Equivalence list saved to {EQUIV_LIST_FILE}")