import os
import json
from typing import List, Dict, Any
from cli_commands.cli_utils import polynomial_to_str

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

    # Convert odds and odws dict keys to integer keys after loading.
    for apn_dict in data["input_apns"]:
        _unify_integer_keys_odds_odws(apn_dict)
        for match_dict in apn_dict.get("matches", []):
            _unify_integer_keys_odds_odws(match_dict)

    return data["input_apns"]

def save_input_apns_and_matches(apn_list: List[Dict[str, Any]]) -> None:
    # Writes the entire input APN + matches structure to input_apns_and_matches.json.
    ensure_storage_folder()

    # Add "poly_str" (Univariate Polynomial representation) for each APN.
    for apn_dict in apn_list:

        if isinstance(apn_dict.get("poly"), list):
            apn_dict["poly_str"] = polynomial_to_str(apn_dict["poly"])

        if "matches" in apn_dict:
            for match_item in apn_dict["matches"]:
                if isinstance(match_item.get("poly"), list):
                    match_item["poly_str"] = polynomial_to_str(match_item["poly"])

    data = {"input_apns": apn_list}

    with open(INPUT_APNS_AND_MATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        # Store arrays in one line (horizontally).
        # json.dump(data, f, indent=None, separators=(",", ":"))

# --------------------------------------------------------------
# equivalence_list.json
# --------------------------------------------------------------
def load_equivalence_list() -> List[Dict[str, Any]]:
    # Loads the equivalences from equivalence_list.json.
    ensure_storage_folder()
    if not os.path.isfile(EQUIVALENCE_LIST_FILE):
        return []
    with open(EQUIVALENCE_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_equivalence_list(eq_list: List[Dict[str, Any]]) -> None:
    ensure_storage_folder()
    with open(EQUIVALENCE_LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(eq_list, f, indent=2)

# --------------------------------------------------------------
# Helper to unify odds and odws dict keys as integers.
# --------------------------------------------------------------
def _unify_integer_keys_odds_odws(apn_dict: Dict[str, Any]) -> None:
    invariants = apn_dict.setdefault("invariants", {})

    # If Ortho-Derivative Differential Spectrum is a dict, cast keys to integers.
    if "odds" in invariants and isinstance(invariants["odds"], dict):
        new_odds = {}
        for k, v in invariants["odds"].items():
            new_odds[int(k)] = int(v)
        invariants["odds"] = new_odds

    # If Ortho-Derivative extended Walsh Spectrum is a dict, cast keys to integers.
    if "odws" in invariants and isinstance(invariants["odws"], dict):
        new_odws = {}
        for k, v in invariants["odws"].items():
            new_odws[int(k)] = int(v)
        invariants["odws"] = new_odws