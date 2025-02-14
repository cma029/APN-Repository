import click
import concurrent.futures
import multiprocessing
from typing import List, Tuple, Dict, Any
from storage.json_storage_utils import (
    load_input_apns_and_matches,
    save_input_apns_and_matches
)
from cli_commands.cli_utils import format_generic_apn
from apn_invariants import compute_all_invariants
from apn_object import APN


@click.command("compute-match-invariants")
@click.option("--input-apn-index", default=None, type=int,
              help="Index of a single input APN whose matches to process.")
@click.option("--max-threads", default=None, type=int,
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
        # A single input APNs matches.
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo("Invalid input APN index.")
            return
        match_list = apn_list[input_apn_index].get("matches", [])
        for match_idx, match_dict in enumerate(match_list):
            tasks.append((input_apn_index, match_idx, match_dict))
    else:
        # All input APNs matches.
        for apn_idx, apn_dict in enumerate(apn_list):
            match_list = apn_dict.get("matches", [])
            for match_idx, match_dictionary in enumerate(match_list):
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
            in_apn_index, match_index, updated_dict, success, error_msg = future.result()
            if not success:
                click.echo(error_msg, err=True)
                updated_dict = None
            match_results[(in_apn_index, match_index)] = updated_dict

    # Merge results.
    for (apn_idx, match_idx), updated_match_dict in match_results.items():
        if updated_match_dict is not None:
            apn_list[apn_idx]["matches"][match_idx] = updated_match_dict

    save_input_apns_and_matches(apn_list)

    if input_apn_index is not None:
        # Matches of a single input APN.
        match_list = apn_list[input_apn_index].get("matches", [])
        click.echo(f"Updated invariants for {len(match_list)} match(es) of INPUT_APN {input_apn_index}.")
        for match_idx, match_dict in enumerate(match_list):
            match_apn = APN(
                match_dict["poly"],
                match_dict["field_n"],
                match_dict["irr_poly"]
            )
            match_apn.invariants = match_dict["invariants"]
            label_str = f"Matches for INPUT_APN {input_apn_index}:"
            click.echo(format_generic_apn(match_apn, label=label_str))
            click.echo("-" * 60)

        click.echo(
            f"Finished computing all invariants for matches of INPUT_APN {input_apn_index} "
            f"(and saved updates)."
        )
    else:
        # All match APNs.
        total_matches_updated = 0
        for idx, apn_dict in enumerate(apn_list):
            match_list = apn_dict.get("matches", [])
            if match_list:
                total_matches_updated += len(match_list)
                for match_dict in match_list:
                    match_apn = APN(
                        match_dict["poly"],
                        match_dict["field_n"],
                        match_dict["irr_poly"]
                    )
                    match_apn.invariants = match_dict["invariants"]
                    label_str = f"Matches for INPUT_APN {idx}:"
                    click.echo(format_generic_apn(match_apn, label=label_str))
                    click.echo("-" * 60)
        click.echo(
            f"Finished computing all invariants for {total_matches_updated} matches among all input APNs "
            f"(and saved updates)."
        )


def _compute_invariants_for_match_apn(task: Tuple[int, int, Dict[str, Any]]) -> Tuple[int, int, Dict[str, Any], bool, str]:
    # Concurrency helper for a single match APN.
    input_apn_index, match_index, match_dictionary = task
    try:
        match_apn = APN(
            match_dictionary["poly"],
            match_dictionary["field_n"],
            match_dictionary["irr_poly"]
        )
        match_apn.invariants = match_dictionary.get("invariants", {})

        compute_all_invariants(match_apn)

        # Update dictionary.
        match_dictionary["invariants"] = match_apn.invariants
        return (input_apn_index, match_index, match_dictionary, True, "")
    except Exception as error:
        return (input_apn_index, match_index, None, False, f"Error computing invariants (match): {error}")