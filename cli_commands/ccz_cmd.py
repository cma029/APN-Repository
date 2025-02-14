import click
import concurrent.futures
from storage.json_storage_utils import (
    load_input_apns_and_matches,
    save_input_apns_and_matches,
    load_equivalence_list,
    save_equivalence_list
)
from computations.equivalence.ccz_equivalence import CCZEquivalenceTest
from apn_object import APN
from representations.truth_table_representation import TruthTableRepresentation
from typing import List, Dict, Any
from collections import defaultdict

@click.command("ccz")
@click.option("--input-apn-index", default=None, type=int,
              help="If specified, only check the matches of that single input APN.")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def ccz_equivalence_cli(input_apn_index, max_threads):
    # Checks CCZ equivalence for the input APNs listed in input_apns_and_matches.json.
    input_apn_list = load_input_apns_and_matches()
    if not input_apn_list:
        click.echo("No input APNs found in storage/input_apns_and_matches.json.")
        return

    if input_apn_index is not None:
        if input_apn_index < 0 or input_apn_index >= len(input_apn_list):
            click.echo(f"Invalid input APN index {input_apn_index}.")
            return
        chosen_input_apns = [input_apn_list[input_apn_index]]
        chosen_indices = [input_apn_index]
    else:
        chosen_input_apns = input_apn_list
        chosen_indices = list(range(len(input_apn_list)))

    # Prepare tasks for concurrency; each task => (apn_idx, match_idx, input_tt, match_tt).
    concurrency_tasks = []
    input_truth_tables_map = {}

    for offset_index, input_apn_dict in enumerate(chosen_input_apns):
        apn_index = chosen_indices[offset_index]

        # Build the input APN object and get its truth table.
        input_apn_object = APN(
            input_apn_dict["poly"],
            input_apn_dict["field_n"],
            input_apn_dict["irr_poly"]
        )
        input_apn_object.invariants = input_apn_dict.get("invariants", {})
        input_truth_table = input_apn_object.get_truth_table().representation.truth_table
        input_truth_tables_map[apn_index] = input_truth_table

        # Build tasks for each match in this APNs matches list.
        match_list = input_apn_dict.get("matches", [])
        for match_index, match_dict in enumerate(match_list):
            match_apn_object = APN(
                match_dict["poly"],
                match_dict["field_n"],
                match_dict["irr_poly"]
            )
            match_apn_object.invariants = match_dict.get("invariants", {})
            match_truth_table = match_apn_object.get_truth_table().representation.truth_table

            concurrency_tasks.append((apn_index, match_index, input_truth_table, match_truth_table))

    if not concurrency_tasks:
        click.echo("No matches to test for CCZ equivalence.")
        return

    # Run concurrency for CCZ checks.
    ccz_equivalence_results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_threads) as executor:
        task_to_indices_map = {}
        for (apn_idx, match_idx, in_tt, mt_tt) in concurrency_tasks:
            submitted_task = executor.submit(_ccz_single, in_tt, mt_tt)
            task_to_indices_map[submitted_task] = (apn_idx, match_idx)

        for completed_task in concurrent.futures.as_completed(task_to_indices_map):
            apn_idx, match_idx = task_to_indices_map[completed_task]
            equivalence_found = completed_task.result()
            ccz_equivalence_results.append((apn_idx, match_idx, equivalence_found))

    equivalence_map = defaultdict(list)
    for (apn_idx, match_idx, eq_bool) in ccz_equivalence_results:
        equivalence_map[apn_idx].append((match_idx, eq_bool))

    # Track which APNs get removed (found at least one CCZ equivalence),
    # and which matches to remove if they are not equivalent.
    removed_apn_indices = set()
    non_equivalent_matches_map = defaultdict(list)

    for apn_idx, match_outcomes in equivalence_map.items():
        # If any match was True => remove that input APN and matches from the file.
        any_equivalent = [(m_idx, True) for (m_idx, eq_bool) in match_outcomes if eq_bool]
        if any_equivalent:
            chosen_match_index = any_equivalent[0][0]
            input_apn_dict = input_apn_list[apn_idx]
            matched_apn_dict = input_apn_dict["matches"][chosen_match_index]
            _store_equivalence_record(input_apn_dict, matched_apn_dict, "ccz")
            removed_apn_indices.add(apn_idx)
        else:
            # If any are False => remove those non-equivalent matches from the input APNs match list.
            failed_match_indexes = [m_idx for (m_idx, eq_bool) in match_outcomes if not eq_bool]
            non_equivalent_matches_map[apn_idx].extend(failed_match_indexes)

    # Build the final list excluding removed APNs.
    filtered_apn_list = []
    for i, apn_dict in enumerate(input_apn_list):
        if i not in removed_apn_indices:
            filtered_apn_list.append(apn_dict)

    # Remove the failed matches from each remaining APN.
    for i, apn_dict in enumerate(input_apn_list):
        if i in removed_apn_indices:
            continue
        failed_indexes = non_equivalent_matches_map.get(i, [])
        if failed_indexes:
            old_matches = apn_dict.get("matches", [])
            new_matches = [
                m_dict for idx_m, m_dict in enumerate(old_matches)
                if idx_m not in failed_indexes
            ]
            apn_dict["matches"] = new_matches

    save_input_apns_and_matches(filtered_apn_list)

    removed_count = len(removed_apn_indices)
    remain_count = len(filtered_apn_list)
    if removed_count > 0:
        click.echo(
            f"{removed_count} input APNs were CCZ-equivalent with a matched APN.\n"
            f"Removed from storage/input_apns_and_matches and recorded in equivalence_list."
        )
    else:
        click.echo("No CCZ equivalences found for the chosen APNs.")

    click.echo(
        f"{remain_count} input APNs (and their matches) remain in storage/input_apns_and_matches.json."
    )


def _ccz_single(input_truth_table, match_truth_table):
    ccz_tester = CCZEquivalenceTest()
    apn_input = APN.from_representation(
        TruthTableRepresentation(input_truth_table), 
        1, 
        "0"
    )
    apn_match = APN.from_representation(
        TruthTableRepresentation(match_truth_table),
        1,
        "0"
    )
    return ccz_tester.are_equivalent(apn_input, apn_match)


def _store_equivalence_record(input_apn_dict: Dict[str, Any], matched_apn_dict: Dict[str, Any], eq_type: str):
    equivalence_list = load_equivalence_list()
    equivalence_list.append({
        "eq_type": eq_type,
        "input_apn": {
            "poly": input_apn_dict["poly"],
            "field_n": input_apn_dict["field_n"],
            "irr_poly": input_apn_dict["irr_poly"],
            "invariants": input_apn_dict.get("invariants", {})
        },
        "matched_apn": {
            "poly": matched_apn_dict["poly"],
            "field_n": matched_apn_dict["field_n"],
            "irr_poly": matched_apn_dict["irr_poly"],
            "invariants": matched_apn_dict.get("invariants", {})
        }
    })
    save_equivalence_list(equivalence_list)