import click
from storage.json_storage_utils import (
    load_input_apns_and_matches,
    save_input_apns_and_matches,
    load_equivalence_list,
    save_equivalence_list
)
from apn_object import APN
import concurrent.futures
from typing import List, Dict, Any
from collections import defaultdict
from representations.truth_table_representation import TruthTableRepresentation
from apn_invariants import compute_k_to_1

@click.command("uni3to1")
@click.option("--input-apn-index", default=None, type=int,
              help="If specified, only check that single APN in the file. Otherwise process all.")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def uni3to1_equivalence_cli(input_apn_index, max_threads):
    # Checks linear equivalence for two 3-to-1 (uniform) APNs.
    input_apn_list = load_input_apns_and_matches()

    if not input_apn_list:
        click.echo("No input APNs found in input_apns_and_matches.json.")
        return

    if input_apn_index is not None:
        if input_apn_index < 0 or input_apn_index >= len(input_apn_list):
            click.echo(f"Invalid input APN index {input_apn_index}.")
            return
        chosen_apns = [input_apn_list[input_apn_index]]
        chosen_indices = [input_apn_index]
    else:
        chosen_apns = input_apn_list
        chosen_indices = list(range(len(input_apn_list)))

    # Prepare tasks for concurrency; each task => (apn_idx, match_idx, input_tt, match_tt).
    tasks = []
    input_truth_tables = {}

    for idx_offset, apn_dictionary in enumerate(chosen_apns):
        absolute_index = chosen_indices[idx_offset]
        _ensure_k_to_1_invariant(apn_dictionary)

        match_list = apn_dictionary.get("matches", [])
        for match_dictionary in match_list:
            _ensure_k_to_1_invariant(match_dictionary)

    for idx_offset, apn_dictionary in enumerate(chosen_apns):
        absolute_index = chosen_indices[idx_offset]

        # Only consider this APN if it has invariant ["k_to_1"]=="3-to-1".
        if apn_dictionary.get("invariants", {}).get("k_to_1") != "3-to-1":
            continue

        # APN object to get Truth Table.
        input_apn_object = APN(
            apn_dictionary["poly"],
            apn_dictionary["field_n"],
            apn_dictionary["irr_poly"]
        )
        input_apn_object.invariants = apn_dictionary.get("invariants", {})
        input_truth_table = input_apn_object.get_truth_table().representation.truth_table
        input_truth_tables[absolute_index] = input_truth_table

        # Build tasks for each match that also have invariant ["k_to_1"]=="3-to-1".
        match_list = apn_dictionary.get("matches", [])
        for match_index, match_dictionary in enumerate(match_list):
            if match_dictionary.get("invariants", {}).get("k_to_1") != "3-to-1":
                continue

            match_apn_object = APN(
                match_dictionary["poly"],
                match_dictionary["field_n"],
                match_dictionary["irr_poly"]
            )
            match_apn_object.invariants = match_dictionary.get("invariants", {})
            match_truth_table = match_apn_object.get_truth_table().representation.truth_table

            tasks.append((absolute_index, match_index, input_truth_table, match_truth_table))

    if not tasks:
        click.echo("No '3-to-1' APNs or matches found to test.")
        return

    results = []  # A list of (apn_index, match_index, equivalence_bool).

    # Concurrency with process-based executor.
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_threads) as executor:
        future_map = {}
        for (apn_idx, match_idx, in_tt, mt_tt) in tasks:
            future = executor.submit(_3to1_single, in_tt, mt_tt)
            future_map[future] = (apn_idx, match_idx)

        for future in concurrent.futures.as_completed(future_map):
            input_index, matching_index = future_map[future]
            equivalence_found = future.result()
            results.append((input_index, matching_index, equivalence_found))

    # Unify the results.
    eq_map = defaultdict(list)  # eq_map[apn_idx] => list of (match_idx, eq_bool).
    for (the_apn_index, the_match_index, eq_bool) in results:
        eq_map[the_apn_index].append((the_match_index, eq_bool))

    removed_indices = set()
    fail_map = defaultdict(list)

    for the_apn_index, pair_list in eq_map.items():
        found_true = [(m_i, True) for (m_i, eq_b) in pair_list if eq_b]
        if found_true:
            # Pick True first.
            chosen_match_idx = found_true[0][0]
            input_apn_dict = input_apn_list[the_apn_index]
            matched_apn_dict = input_apn_dict["matches"][chosen_match_idx]
            _store_equivalence_record(input_apn_dict, matched_apn_dict, "uni3to1")

            removed_indices.add(the_apn_index)
        else:
            # If none, then remove fails (False).
            fails = [m_i for (m_i, eq_b) in pair_list if not eq_b]
            fail_map[the_apn_index].extend(fails)

    final_list = []
    for i, apn_dict in enumerate(input_apn_list):
        if i not in removed_indices:
            final_list.append(apn_dict)

    for i, apn_dict in enumerate(input_apn_list):
        if i in removed_indices:
            continue
        fails = fail_map.get(i, [])
        if fails:
            old_matches = apn_dict.get("matches", [])
            new_matches = [
                match_dictionary for idx_m, match_dictionary in enumerate(old_matches)
                if idx_m not in fails
            ]
            apn_dict["matches"] = new_matches

    save_input_apns_and_matches(final_list)

    removed_count = len(removed_indices)
    remain_count = len(final_list)
    if removed_count > 0:
        click.echo(
            f"{removed_count} input APN(s) found 3-to-1 equivalence, removed from the file "
            f"and stored in equivalence_list."
        )
    else:
        click.echo("No 3-to-1 equivalences found for the chosen APN(s).")

    click.echo(
        f"{remain_count} input APNs (and their matches) remain in storage/input_apns_and_matches.json."
    )


def _3to1_single(input_truth_table, match_truth_table):
    from computations.equivalence.lin_eq_2x_uniform_3to1 import Uniform3to1EquivalenceTest
    from apn_object import APN
    from representations.truth_table_representation import TruthTableRepresentation

    test_equivalence = Uniform3to1EquivalenceTest()
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
    return test_equivalence.are_equivalent(apn_input, apn_match)


def _store_equivalence_record(input_apn_dict: Dict[str,Any], matched_apn_dict: Dict[str,Any], eq_type: str):
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


def _ensure_k_to_1_invariant(apn_dictionary: Dict[str,Any]):
    invariants = apn_dictionary.setdefault("invariants", {})
    if "k_to_1" in invariants:
        return  # If already present.

    apn_obj = APN(
        apn_dictionary["poly"],
        apn_dictionary["field_n"],
        apn_dictionary["irr_poly"]
    )
    apn_obj.invariants = invariants

    try:
        k_val = compute_k_to_1(apn_obj)
        invariants["k_to_1"] = k_val
    except:
        invariants["k_to_1"] = "non-uniform"