import click
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
import concurrent.futures
from typing import List


@click.command("compare")
@click.option("--compare-type", type=click.Choice(["odds", "odws", "delta", "gamma", "all"]), 
              default="all", help="Which invariants to compare. 'all' means delta, gamma, odds, odws.")
@click.option("--field-n", required=True, type=int, help="The dimension n for GF(2^n).")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def compare_apns_cli(field_n, compare_type, max_threads):
    # Compares invariants of input APNs with the invariants of stored database APNs for GF(2^n).
    # Invariants are computed when needed, and matches are stored storage/input_apns_and_matches.json.
    input_apn_list = load_input_apns_and_matches()
    if not input_apn_list:
        click.echo("No input APNs found. Please run 'add-input' first.")
        return

    database_apns = load_apn_objects_for_field_pandas(field_n)
    if not database_apns:
        click.echo(f"No APNs found in the DB for GF(2^{field_n}).")
        return

    if compare_type == "all":
        compare_types = ["delta", "gamma", "odds", "odws"]
    else:
        compare_types = [compare_type]

    concurrency_tasks = [
        (idx, apn_dict, database_apns, compare_types)
        for idx, apn_dict in enumerate(input_apn_list)
    ]

    number_of_workers = max_threads if max_threads else None
    task_to_index_map = {}
    results = []

    # Concurrency with process-based executor.
    with concurrent.futures.ProcessPoolExecutor(max_workers=number_of_workers) as executor:
        for task_item in concurrency_tasks:
            index_in_list = task_item[0]
            apn_task = executor.submit(_compare_single_apn, task_item)
            task_to_index_map[apn_task] = index_in_list

        for apn_task in concurrent.futures.as_completed(task_to_index_map):
            index_in_list = task_to_index_map[apn_task]
            (updated_apn_dictionary, matched_apns) = apn_task.result()
            results.append((index_in_list, updated_apn_dictionary, matched_apns))

    # Merge the results => store matched_list in input_apn_list[idx]["matches"].
    for (idx_in_list, updated_apn_dictionary, matched_list) in results:
        input_apn_list[idx_in_list]["matches"] = matched_list
        input_apn_list[idx_in_list]["invariants"] = updated_apn_dictionary.get("invariants", {})

    save_input_apns_and_matches(input_apn_list)

    for idx, apn_dictionary in enumerate(input_apn_list):
        current_matches = apn_dictionary.get("matches", [])
        click.echo(
            f"For INPUT_APN {idx}, found {len(current_matches)} matches after comparing by '{compare_type}'."
        )

    click.echo("Finished comparing APNs and stored matches in their 'matches' list.")


def _compare_single_apn(task_tuple):
    (idx_in_list, apn_dictionary, database_apns, compare_types) = task_tuple

    # Build APN object.
    input_apn_object = APN(
        apn_dictionary["poly"],
        apn_dictionary["field_n"],
        apn_dictionary["irr_poly"]
    )
    input_apn_object.invariants = apn_dictionary.get("invariants", {})

    # Possibly compute needed invariants.
    _compute_invariants_for_compare(input_apn_object, compare_types)

    # Compare with the database.
    matched_list = []
    for db_apn_object in database_apns:
        if _apn_matches(input_apn_object, db_apn_object, compare_types):
            matched_apn_dict = {
                "poly": db_apn_object.representation.univariate_polynomial,
                "field_n": db_apn_object.field_n,
                "irr_poly": db_apn_object.irr_poly,
                "invariants": db_apn_object.invariants,
                "compare_types": compare_types
            }
            matched_list.append(matched_apn_dict)

    apn_dictionary["invariants"] = input_apn_object.invariants
    return (apn_dictionary, matched_list)


def _compute_invariants_for_compare(apn_object: APN, compare_types: List[str]):
    # If we need 'odds' or 'odws', we need to check is_quadratic first.
    if any(ct in compare_types for ct in ["odds", "odws"]):
        _ensure_is_quadratic(apn_object)

    if "delta" in compare_types:
        _compute_delta_rank_direct(apn_object)
    if "gamma" in compare_types:
        _compute_gamma_rank_direct(apn_object)
    if "odds" in compare_types:
        _compute_odds_direct(apn_object)
    if "odws" in compare_types:
        _compute_odws_direct(apn_object)

def _ensure_is_quadratic(apn_object: APN):
    if "is_quadratic" in apn_object.invariants:
        return
    try:
        compute_anf_invariants(apn_object)

    except Exception:
        apn_object.invariants["is_quadratic"] = False


def _compute_delta_rank_direct(apn_object: APN):
    if "delta_rank" not in apn_object.invariants:
        try:
            delta_comp = DeltaRankComputation()
            rank_value = delta_comp.compute_rank(apn_object)
            apn_object.invariants["delta_rank"] = rank_value
        except Exception as err:
            print(f"Error computing delta rank: {err}")
            apn_object.invariants["delta_rank"] = None


def _compute_gamma_rank_direct(apn_object: APN):
    if "gamma_rank" not in apn_object.invariants:
        try:
            gamma_comp = GammaRankComputation()
            rank_value = gamma_comp.compute_rank(apn_object)
            apn_object.invariants["gamma_rank"] = rank_value
        except Exception as err:
            print(f"Error computing gamma rank: {err}")
            apn_object.invariants["gamma_rank"] = None


def _compute_odds_direct(apn_object: APN):
    if "odds" in apn_object.invariants:
        return
    is_quad = apn_object.invariants.get("is_quadratic", False)
    if is_quad:
        try:
            tt_list = apn_object._get_truth_table_list()
            dimension = apn_object.field_n
            odds_result = vbf_tt_differential_spectrum_python(tt_list, dimension)
            apn_object.invariants["odds"] = {int(k): int(v) for k, v in odds_result.items()}
        except Exception as err:
            print(f"Error computing the Ortho-Derivative Differential Spectrum: {err}")
            apn_object.invariants["odds"] = "non-quadratic"
    else:
        apn_object.invariants.setdefault("odds", "non-quadratic")


def _compute_odws_direct(apn_object: APN):
    if "odws" in apn_object.invariants:
        return
    is_quad = apn_object.invariants.get("is_quadratic", False)
    if is_quad:
        try:
            tt_list = apn_object._get_truth_table_list()
            dimension = apn_object.field_n
            odws_result = vbf_tt_extended_walsh_spectrum_python(tt_list, dimension)
            apn_object.invariants["odws"] = {int(k): int(v) for k, v in odws_result.items()}
        except Exception as err:
            print(f"Error computing the Ortho-Derivative extended Walsh Spectrum: {err}")
            apn_object.invariants["odws"] = "non-quadratic"
    else:
        apn_object.invariants.setdefault("odws", "non-quadratic")


def _apn_matches(input_apn_object: APN, database_apn_object: APN, compare_types: List[str]) -> bool:
    # Checks if input APN object matches database APN object on each compare type:
    input_invs = input_apn_object.invariants
    db_invs = database_apn_object.invariants

    for comparison_type in compare_types:
        if comparison_type == "delta":
            if input_invs.get("delta_rank") != db_invs.get("delta_rank"):
                return False
        elif comparison_type == "gamma":
            if input_invs.get("gamma_rank") != db_invs.get("gamma_rank"):
                return False
        elif comparison_type == "odds":
            if input_invs.get("odds") != db_invs.get("odds"):
                return False
        elif comparison_type == "odws":
            if input_invs.get("odws") != db_invs.get("odws"):
                return False
    return True