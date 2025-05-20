import json
from pathlib import Path
from typing import List, Dict, Any
from cli_commands.cli_utils import polynomial_to_str

STORAGE_DIR = "storage"
INPUT_VBFS_AND_MATCHES_FILE = Path(STORAGE_DIR) / "input_vbfs_and_matches.json"
EQUIVALENCE_LIST_FILE = Path(STORAGE_DIR) / "equivalence_list.json"

def ensure_storage_folder():
    storage_path = Path(STORAGE_DIR)
    if not storage_path.is_dir():
        storage_path.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------
# input_vbfs_and_matches.json
# --------------------------------------------------------------
def load_input_vbfs_and_matches() -> List[Dict[str, Any]]:
    # Reads VBFs from input_vbfs_and_matches.json and returns them as a list of VBF objects.
    ensure_storage_folder()
    if not INPUT_VBFS_AND_MATCHES_FILE.is_file():
        return []
    with INPUT_VBFS_AND_MATCHES_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "input_vbfs" not in data:
        return []

    # Convert odds and odws dict keys to integer keys after loading.
    for vbf_dictionary in data["input_vbfs"]:
        _unify_integer_keys_odds_odws(vbf_dictionary)
        for match_dict in vbf_dictionary.get("matches", []):
            _unify_integer_keys_odds_odws(match_dict)

    return data["input_vbfs"]

def save_input_vbfs_and_matches(vbf_list: List[Dict[str, Any]]) -> None:
    # Writes the entire input VBF + matches structure to input_vbfs_and_matches.json.
    ensure_storage_folder()

    # Add "poly_str" (Univariate Polynomial representation) for each VBF.
    for vbf_dictionary in vbf_list:

        if isinstance(vbf_dictionary.get("poly"), list):
            vbf_dictionary["poly_str"] = polynomial_to_str(vbf_dictionary["poly"])

        if "matches" in vbf_dictionary:
            for match_item in vbf_dictionary["matches"]:
                if isinstance(match_item.get("poly"), list):
                    match_item["poly_str"] = polynomial_to_str(match_item["poly"])

    data = {"input_vbfs": vbf_list}

    with INPUT_VBFS_AND_MATCHES_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        # Store arrays in one line (horizontally).
        # json.dump(data, f, indent=None, separators=(",", ":"))

# --------------------------------------------------------------
# equivalence_list.json
# --------------------------------------------------------------
def load_equivalence_list() -> List[Dict[str, Any]]:
    # Loads the equivalences from equivalence_list.json.
    ensure_storage_folder()
    if not EQUIVALENCE_LIST_FILE.is_file():
        return []
    with EQUIVALENCE_LIST_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_equivalence_list(eq_list: List[Dict[str, Any]]) -> None:
    ensure_storage_folder()
    with EQUIVALENCE_LIST_FILE.open("w", encoding="utf-8") as f:
        json.dump(eq_list, f, indent=2)

# --------------------------------------------------------------
# Helper to unify odds and odws dict keys as integers.
# --------------------------------------------------------------
def _unify_integer_keys_odds_odws(vbf_dictionary: Dict[str, Any]) -> None:
    invariants = vbf_dictionary.setdefault("invariants", {})

    # If Ortho-Derivative Differential Spectrum is a dict, cast keys to integers.
    if "odds" in invariants and isinstance(invariants["odds"], dict):
        new_odds = {}
        for key, val in invariants["odds"].items():
            new_odds[int(key)] = int(val)
        invariants["odds"] = new_odds

    # If Ortho-Derivative extended Walsh Spectrum is a dict, cast keys to integers.
    if "odws" in invariants and isinstance(invariants["odws"], dict):
        new_odws = {}
        for key, val in invariants["odws"].items():
            new_odws[int(key)] = int(val)
        invariants["odws"] = new_odws