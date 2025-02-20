import click
import concurrent.futures
from typing import List, Tuple, Dict, Any
from storage.json_storage_utils import (
    load_input_apns_and_matches,
    save_input_apns_and_matches
)
from cli_commands.cli_utils import format_generic_apn
from apn_invariants import compute_all_invariants
from apn_object import APN

@click.command("compute-match-invariants")
@click.option("--index", "input_apn_index", default=None, type=int,
              help="Index of a single input APN whose matches to process.")
@click.option("--max-threads", "max_threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def compute_match_invariants_cli(input_apn_index, max_threads):
    # Computes all invariants for the match APNs (not their input).
    apn_list = load_input_apns_and_matches()
    if not apn_list:
        click.echo("No APNs in input list. Please run 'add-input' first.")
        return

    # Build tasks for concurrency.
    tasks: List[Tuple[int, int, Dict[str, Any]]] = []
    if input_apn_index is not None:
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo("Invalid input APN index.")
            return
        match_list = apn_list[input_apn_index].get("matches", [])
        for match_idx, match_dict in enumerate(match_list):
            tasks.append((input_apn_index, match_idx, match_dict))
    else:
        for apn_idx, apn_dict in enumerate(apn_list):
            for match_idx, match_dictionary in enumerate(apn_dict.get("matches", [])):
                tasks.append((apn_idx, match_idx, match_dictionary))

    if not tasks:
        click.echo("No matches found. Possibly run 'compare' first.")
        return

    number_of_workers = max_threads if max_threads else None
    match_results: Dict[Tuple[int, int], Dict[str, Any]] = {}

    # Concurrency with process-based executor.
    with concurrent.futures.ProcessPoolExecutor(max_workers=number_of_workers) as executor:
        future_list = [executor.submit(_compute_invariants_for_match_apn, t) for t in tasks]
        for future in concurrent.futures.as_completed(future_list):
            returned_apn_index, returned_match_index, updated_match_dict = future.result()
            match_results[(returned_apn_index, returned_match_index)] = updated_match_dict

    # Merge results.
    for (apn_idx, match_idx), updated_match_dict in match_results.items():
        apn_list[apn_idx]["matches"][match_idx] = updated_match_dict

    save_input_apns_and_matches(apn_list)

    if input_apn_index is not None:
        match_list = apn_list[input_apn_index].get("matches", [])
        click.echo(f"Updated invariants for {len(match_list)} matches of APN {input_apn_index}.")
        for match_dict in match_list:
            match_apn = _build_apn_from_dict(match_dict)
            click.echo(format_generic_apn(match_apn, f"Matches for INPUT_APN {input_apn_index}:"))
            click.echo("-" * 100)
    else:
        total = 0
        for apn_idx, apn_dict in enumerate(apn_list):
            ms = apn_dict.get("matches", [])
            total += len(ms)
            for match_dict in ms:
                match_apn = _build_apn_from_dict(match_dict)
                click.echo(format_generic_apn(match_apn, f"Matches for INPUT_APN {apn_idx}:"))
                click.echo("-" * 100)
        click.echo(f"Finished computing invariants for {total} matches.")


def _compute_invariants_for_match_apn(task: Tuple[int, int, Dict[str, Any]]):
    input_apn_index, match_index, match_dictionary = task
    if "cached_tt" in match_dictionary and match_dictionary["cached_tt"]:
        match_apn = APN.from_cached_tt(
            match_dictionary["cached_tt"],
            match_dictionary["field_n"],
            match_dictionary["irr_poly"]
        )
    else:
        match_apn = APN(
            match_dictionary["poly"],
            match_dictionary["field_n"],
            match_dictionary["irr_poly"]
        )
    match_apn.invariants = match_dictionary.get("invariants", {})

    match_apn._get_truth_table_list()
    compute_all_invariants(match_apn)
    match_dictionary["invariants"] = match_apn.invariants

    return (input_apn_index, match_index, match_dictionary)


def _build_apn_from_dict(dict: Dict[str, Any]) -> APN:
    if "cached_tt" in dict and dict["cached_tt"]:
        apn_obj = APN.from_cached_tt(dict["cached_tt"], dict["field_n"], dict["irr_poly"])
    else:
        apn_obj = APN(dict["poly"], dict["field_n"], dict["irr_poly"])
    apn_obj.invariants = dict.get("invariants", {})
    return apn_obj