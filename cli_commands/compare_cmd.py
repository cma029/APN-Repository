import click
import concurrent.futures
from typing import Tuple, List, Dict, Any
from storage.json_storage_utils import (
    load_input_apns_and_matches,
    save_input_apns_and_matches
)
from c_spectra_bindings import (
    vbf_tt_differential_spectrum_python,
    vbf_tt_extended_walsh_spectrum_python
)
from computations.rank.delta_rank import DeltaRankComputation
from computations.rank.gamma_rank import GammaRankComputation
from apn_storage_pandas import load_apn_objects_for_field_pandas
from apn_invariants import compute_anf_invariants
from apn_object import APN


@click.command("compare")
@click.option("--type", "compare_type", type=click.Choice(["odds", "odws", "delta", "gamma", "all"]),
              default="all", help="Which invariants to compare. 'all' means delta, gamma, odds, odws.")
@click.option("--field-n", required=True, type=int, help="The dimension n for GF(2^n).")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def compare_apns_cli(field_n, compare_type, max_threads):
    # Compares invariants of input APNs with the invariants of stored database APNs for GF(2^n).
    # Invariants are computed when needed, and matches are stored in storage/input_apns_and_matches.json.

    input_apn_list = load_input_apns_and_matches()
    if not input_apn_list:
        click.echo("No input APNs found. Please run 'add-input' first.")
        return

    db_apn_list = load_apn_objects_for_field_pandas(field_n)
    if not db_apn_list:
        click.echo(f"No APNs found in the DB for GF(2^{field_n}).")
        return

    if compare_type == "all":
        invariants_to_compare = ["odds", "odws", "delta", "gamma"]
    else:
        invariants_to_compare = [compare_type]

    # Not possible to select delta and gamma ranks for field-n dimensions larger than 10.
    if field_n > 10:
        filtered = [invariants for invariants in invariants_to_compare if invariants not in ("delta", "gamma")]
        removed = set(invariants_to_compare) - set(filtered)
        if removed:
            click.echo(f"Warning: {', '.join(removed)} not supported for n > 10. Skipping those invariants.")
        invariants_to_compare = filtered

    if not invariants_to_compare:
        click.echo("No valid invariants remain to compare. Exiting.")
        return

    # Concurrency: compute any missing invariants in the input APNs.
    tasks = [
        (idx, apn_dict, invariants_to_compare)
        for idx, apn_dict in enumerate(input_apn_list)
    ]
    max_procs = max_threads or None

    updated_map: Dict[int, Dict[str, Any]] = {}

    # Concurrency with process-based executor.
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_procs) as executor:
        future_map = {}
        for task_tuple in tasks:
            future_obj = executor.submit(_compute_invariants_for_input_apn, task_tuple)
            future_map[future_obj] = task_tuple[0]

        for done_fut in concurrent.futures.as_completed(future_map):
            idx_val = future_map[done_fut]
            updated_dict = done_fut.result()
            updated_map[idx_val] = updated_dict

    # Merge concurrency results.
    for i in range(len(input_apn_list)):
        if i in updated_map:
            input_apn_list[i] = updated_map[i]

    # For each input APN => first-time search or narrow the matches.
    for i, input_apn_data in enumerate(input_apn_list):
        existing_matches = input_apn_data.get("matches", None)
        if not existing_matches:
            # Full database search (if no matches exist yet).
            fresh_matches = []
            in_invs = input_apn_data["invariants"]
            for db_apn_obj in db_apn_list:
                if _apn_matches(in_invs, db_apn_obj.invariants, invariants_to_compare):
                    match_dict = {
                        "poly": db_apn_obj.representation.univariate_polynomial,
                        "field_n": db_apn_obj.field_n,
                        "irr_poly": db_apn_obj.irr_poly,
                        "invariants": db_apn_obj.invariants,
                        "compare_types": list(invariants_to_compare)
                    }
                    fresh_matches.append(match_dict)
            input_apn_data["matches"] = fresh_matches
        else:
            # Narrow existing matches.
            in_invs = input_apn_data["invariants"]
            narrowed = []
            for match_item in existing_matches:
                db_invs = match_item.get("invariants", {})
                if _apn_matches(in_invs, db_invs, invariants_to_compare):
                    old_list = match_item.get("compare_types", [])
                    union_ = set(old_list).union(set(invariants_to_compare))
                    match_item["compare_types"] = list(union_)
                    narrowed.append(match_item)
            input_apn_data["matches"] = narrowed

    save_input_apns_and_matches(input_apn_list)

    for idx, item in enumerate(input_apn_list):
        ccount = len(item.get("matches", []))
        click.echo(f"For INPUT_APN {idx}, found {ccount} matches after comparing by '{compare_type}'.")
    click.echo("Done compare.")


def _compute_invariants_for_input_apn(task_tuple: Tuple[int, Dict[str, Any], List[str]]) -> Dict[str, Any]:
    # If the input APN is missing 'odds', 'odws', 'delta' or 'gamma' then compute them.
    idx_val, apn_dictionary, wanted_invariants = task_tuple

    # Rebuild the APN object
    poly_data = apn_dictionary.get("poly", [])
    cached_tt = apn_dictionary.get("cached_tt", [])
    if poly_data:
        new_apn = APN(poly_data, apn_dictionary["field_n"], apn_dictionary["irr_poly"])
        if cached_tt:
            new_apn._cached_tt_list = cached_tt
    elif cached_tt:
        new_apn = APN.from_cached_tt(cached_tt, apn_dictionary["field_n"], apn_dictionary["irr_poly"])
    else:
        new_apn = APN([], apn_dictionary["field_n"], apn_dictionary["irr_poly"])

    new_apn.invariants = apn_dictionary.get("invariants", {})
    local_invs = new_apn.invariants

    # Delta rank computation.
    if "delta" in wanted_invariants and "delta_rank" not in local_invs:
        delta_comp = DeltaRankComputation()
        local_invs["delta_rank"] = delta_comp.compute_rank(new_apn)

    # Gamma rank computation.
    if "gamma" in wanted_invariants and "gamma_rank" not in local_invs:
        gamma_comp = GammaRankComputation()
        local_invs["gamma_rank"] = gamma_comp.compute_rank(new_apn)

    # Ortho-Derivative Differential Spectrum.
    if "odds" in wanted_invariants and "odds" not in local_invs:
        if _check_is_quadratic(new_apn):
            dimension = new_apn.field_n
            tt_list = new_apn._get_truth_table_list()
            result_spectrum = vbf_tt_differential_spectrum_python(tt_list, dimension)
            local_invs["odds"] = {int(key): int(val) for key, val in result_spectrum.items()}
        else:
            local_invs["odds"] = "non-quadratic"

    # Ortho-Derivative extended Walsh Spectrum.
    if "odws" in wanted_invariants and "odws" not in local_invs:
        if _check_is_quadratic(new_apn):
            dimension = new_apn.field_n
            tt_list = new_apn._get_truth_table_list()
            result_odws = vbf_tt_extended_walsh_spectrum_python(tt_list, dimension)
            local_invs["odws"] = {int(key): int(val) for key, val in result_odws.items()}
        else:
            local_invs["odws"] = "non-quadratic"

    apn_dictionary["invariants"] = new_apn.invariants
    return apn_dictionary

def _check_is_quadratic(apn_obj: APN) -> bool:
    # If we need 'odds' or 'odws', we need to check is_quadratic first.
    if "is_quadratic" in apn_obj.invariants:
        return apn_obj.invariants["is_quadratic"]
    compute_anf_invariants(apn_obj)
    return bool(apn_obj.invariants.get("is_quadratic", False)) # False => Fallback.

def _apn_matches(in_invariants: dict, db_invariants: dict, invariants_list: List[str]) -> bool:
    # Compare the chosen invariants.
    for inv_type in invariants_list:
        if inv_type == "delta":
            if "delta_rank" not in db_invariants:
                return False
            user_val = _try_int(in_invariants.get("delta_rank"))
            db_val   = _try_int(db_invariants.get("delta_rank"))
            if user_val is None or db_val is None or user_val != db_val:
                return False

        elif inv_type == "gamma":
            if "gamma_rank" not in db_invariants:
                return False
            user_val = _try_int(in_invariants.get("gamma_rank"))
            db_val   = _try_int(db_invariants.get("gamma_rank"))
            if user_val is None or db_val is None or user_val != db_val:
                return False

        elif inv_type == "odds":
            if "odds" not in db_invariants:
                return False
            if not _compare_spectrum(
                in_invariants.get("odds","non-quadratic"),
                db_invariants.get("odds","non-quadratic")
            ):
                return False

        elif inv_type == "odws":
            if "odws" not in db_invariants:
                return False
            if not _compare_spectrum(
                in_invariants.get("odws","non-quadratic"),
                db_invariants.get("odws","non-quadratic")
            ):
                return False

    return True

def _try_int(val):
    if val is None:
        return None
    try:
        return int(val)
    except:
        return None

def _compare_spectrum(in_val, db_val) -> bool:
    if in_val == "non-quadratic" or db_val == "non-quadratic":
        return (in_val == db_val)

    in_dict = _int_key_dict(in_val)
    db_dict = _int_key_dict(db_val)
    return (in_dict == db_dict)

def _int_key_dict(data_candidate):
    import json
    if isinstance(data_candidate, dict):
        result_dict = {}
        for key, val in data_candidate.items():
            result_dict[int(key)] = int(val)
        return result_dict
    if isinstance(data_candidate, str):
        if data_candidate == "non-quadratic":
            return "non-quadratic"
        try:
            parsed = json.loads(data_candidate)
            if isinstance(parsed, dict):
                final_dict = {}
                for parsed_key, parsed_val in parsed.items():
                    final_dict[int(parsed_key)] = int(parsed_val)
                return final_dict
            return parsed
        except:
            return data_candidate
    return data_candidate