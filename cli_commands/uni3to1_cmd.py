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
from cli_commands.cli_utils import polynomial_to_str
from computations.equivalence.lin_eq_2x_uniform_3to1 import (
    Uniform3to1EquivalenceTest,
    is_canonical_triplicate_py
)

@click.command("uni3to1")
@click.option("--input-apn-index", default=None, type=int,
              help="If specified, only check that single APN in the file. Otherwise process all.")
@click.option("--check", is_flag=True,
              help="If specified, we only mark invariants['uni3to1']=True/False via is_canonical_triplicate_py.")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def uni3to1_equivalence_cli(input_apn_index, max_threads, check):
    # Command for checking '3-to-1' (triplicate) linear equivalence using nskal/tripeq's alg1.c.
    input_apn_list = load_input_apns_and_matches()
    if not input_apn_list:
        click.echo("No input APNs found in storage/input_apns_and_matches.json.")
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

    # Check all input and match APNs for is_canonical_triplicate True/False.
    if check:
        _mark_uni3to1_all(chosen_apns, chosen_indices, force=True)
        save_input_apns_and_matches(input_apn_list)
        click.echo("Finished marking invariants['uni3to1'] for chosen APNs.")
        return

    # Only set is_canonical_triplicate True/False if missing.
    _mark_uni3to1_all(chosen_apns, chosen_indices, force=False)
    save_input_apns_and_matches(input_apn_list)

    # Build concurrency tasks only for input/matches with invariants["uni3to1"]==True.
    tasks = []
    for offset_index, apn_dict in enumerate(chosen_apns):
        apn_index = chosen_indices[offset_index]

        in_apn_obj = APN(
            apn_dict["poly"],
            apn_dict["field_n"],
            apn_dict["irr_poly"]
        )
        in_apn_obj.invariants = apn_dict.get("invariants", {})

        if not in_apn_obj.invariants.get("uni3to1", False):
            # Skip if not a canonical triplicate.
            continue

        match_list = apn_dict.get("matches", [])
        for match_idx, match_dict in enumerate(match_list):
            mt_apn_obj = APN(
                match_dict["poly"],
                match_dict["field_n"],
                match_dict["irr_poly"]
            )
            mt_apn_obj.invariants = match_dict.get("invariants", {})

            if not mt_apn_obj.invariants.get("uni3to1", False):
                continue
            # Simple field n dimension check for safety.
            if in_apn_obj.field_n != mt_apn_obj.field_n:
                continue

            tasks.append((apn_index, match_idx, in_apn_obj, mt_apn_obj))

    if not tasks:
        click.echo("No matches found to test for uniformly distributed 3-to-1 equivalence.")
        return

    test_equiv = Uniform3to1EquivalenceTest()
    results = []
    max_procs = max_threads or None

    # Concurrency with process-based executor.
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_procs) as executor:
        fut_map = {}
        for (apn_idx, mt_idx, in_apn, mt_apn) in tasks:
            fut = executor.submit(_equiv_worker, test_equiv, in_apn, mt_apn)
            fut_map[fut] = (apn_idx, mt_idx)

        for done_fut in concurrent.futures.as_completed(fut_map):
            (the_apn_idx, the_match_idx) = fut_map[done_fut]
            eq_bool_or_none = done_fut.result()
            results.append((the_apn_idx, the_match_idx, eq_bool_or_none))

    eq_map = defaultdict(list)
    for (apn_i, match_i, eqval) in results:
        eq_map[apn_i].append((match_i, eqval))

    removed_indices = set()
    fail_map = defaultdict(list)

    for the_apn_index, pair_list in eq_map.items():
        found_true = [(m_idx, True) for (m_idx, val) in pair_list if val is True]
        if found_true:
            chosen_m = found_true[0][0]
            input_apn_dict = input_apn_list[the_apn_index]
            matched_dict = input_apn_dict["matches"][chosen_m]
            _store_equivalence_record(input_apn_dict, matched_dict, "uni3to1")
            removed_indices.add(the_apn_index)
        else:
            fails = [m_idx for (m_idx, val) in pair_list if val is False]
            fail_map[the_apn_index].extend(fails)

    final_list = []
    for i, a_dict in enumerate(input_apn_list):
        if i not in removed_indices:
            final_list.append(a_dict)

    for i, a_dict in enumerate(input_apn_list):
        if i in removed_indices:
            continue
        failing_idxs = fail_map.get(i, [])
        if failing_idxs:
            old_matches = a_dict.get("matches", [])
            new_matches = [
                m_item for idx_m, m_item in enumerate(old_matches)
                if idx_m not in failing_idxs
            ]
            a_dict["matches"] = new_matches

    save_input_apns_and_matches(final_list)
    removed_count = len(removed_indices)
    remain_count = len(final_list)

    if removed_count > 0:
        click.echo(
            f"{removed_count} input APN(s) found 3-to-1 equivalence and are removed from file."
        )
    else:
        click.echo("No 3-to-1 equivalences found (or error has occurred).")

    click.echo(
        f"{remain_count} input APNs remain in storage/input_apns_and_matches.json."
    )


def _equiv_worker(eq_obj, apn_in, apn_mt):
    """
    Concurrency worker returns:
       True => equal.
       False => not equal.
       None => error has occurred.
    """
    try:
        return eq_obj.are_equivalent(apn_in, apn_mt)
    except Exception:
        return None


def _store_equivalence_record(input_apn_dict, matched_apn_dict, eq_type):
    poly_str = polynomial_to_str(input_apn_dict["poly"])
    match_poly_str = polynomial_to_str(matched_apn_dict["poly"])

    eq_list = load_equivalence_list()
    eq_list.append({
        "eq_type": eq_type,
        "input_apn": {
            "poly": input_apn_dict["poly"],
            "poly_str": poly_str,
            "field_n": input_apn_dict["field_n"],
            "irr_poly": input_apn_dict["irr_poly"],
            "invariants": input_apn_dict.get("invariants", {})
        },
        "matched_apn": {
            "poly": matched_apn_dict["poly"],
            "poly_str": match_poly_str,
            "field_n": matched_apn_dict["field_n"],
            "irr_poly": matched_apn_dict["irr_poly"],
            "invariants": matched_apn_dict.get("invariants", {})
        }
    })
    save_equivalence_list(eq_list)


def _mark_uni3to1_all(chosen_apns, chosen_indices, force=False):
    # Check and mark invariants["uni3to1"] for input APNs and matches.
    for offset, apn_dict in enumerate(chosen_apns):
        apn_obj = APN(apn_dict["poly"], apn_dict["field_n"], apn_dict["irr_poly"])
        apn_obj.invariants = apn_dict.get("invariants", {})

        if force or ("uni3to1" not in apn_obj.invariants):
            dimension = apn_obj.field_n
            tt_list = apn_obj._get_truth_table_list()
            if len(tt_list) == (1 << dimension):
                apn_obj.invariants["uni3to1"] = bool(is_canonical_triplicate_py(tt_list, dimension))
            else:
                apn_obj.invariants["uni3to1"] = False
            apn_dict["invariants"] = apn_obj.invariants

        # Matches.
        for mt_item in apn_dict.get("matches", []):
            mt_obj = APN(mt_item["poly"], mt_item["field_n"], mt_item["irr_poly"])
            mt_obj.invariants = mt_item.get("invariants", {})
            if force or ("uni3to1" not in mt_obj.invariants):
                dim2 = mt_obj.field_n
                mt_tt_list = mt_obj._get_truth_table_list()
                if len(mt_tt_list) == (1 << dim2):
                    mt_obj.invariants["uni3to1"] = bool(is_canonical_triplicate_py(mt_tt_list, dim2))
                else:
                    mt_obj.invariants["uni3to1"] = False
                mt_item["invariants"] = mt_obj.invariants