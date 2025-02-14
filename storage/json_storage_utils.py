import os
import json
import click
from typing import List, Dict, Any

STORAGE_DIR = "storage"
INPUT_APNS_AND_MATCHES_FILE = os.path.join(STORAGE_DIR, "input_apns_and_matches.json")
EQUIVALENCE_LIST_FILE = os.path.join(STORAGE_DIR, "equivalence_list.json")

def ensure_storage_folder():
    if not os.path.isdir(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)

# --------------------------------------------------------------
# input_apns_and_matches.json
# --------------------------------------------------------------
def load_input_apns_and_matches() -> List[Dict[str, Any]]:
    # Reads APNs from input_apns_and_matches.json and returns them as a list of APN objects.
    ensure_storage_folder()
    if not os.path.isfile(INPUT_APNS_AND_MATCHES_FILE):
        return []
    with open(INPUT_APNS_AND_MATCHES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "input_apns" not in data:
        return []
    return data["input_apns"]

def save_input_apns_and_matches(apn_list: List[Dict[str, Any]]) -> None:
    # Writes the entire input APN + matches structure to input_apns_and_matches.json.
    ensure_storage_folder()
    data = {"input_apns": apn_list}
    with open(INPUT_APNS_AND_MATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --------------------------------------------------------------
# equivalence_list.json
# --------------------------------------------------------------
def load_equivalence_list() -> List[Dict[str, Any]]:
    # Loads the equivalences from equivalence_list.json, 
    ensure_storage_folder()
    if not os.path.isfile(EQUIVALENCE_LIST_FILE):
        return []
    with open(EQUIVALENCE_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_equivalence_list(eq_list: List[Dict[str, Any]]) -> None:
    ensure_storage_folder()
    with open(EQUIVALENCE_LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(eq_list, f, indent=2)