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


@click.command("compute-input-invariants")
@click.option("--input-apn-index", default=None, type=int,
              help="Index of a single input APN to process.")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def compute_input_invariants_cli(input_apn_index, max_threads):
    # Computes all invariants for the input APNs (not their matches).
    apn_list = load_input_apns_and_matches()
    if not apn_list:
        click.echo("No APNs in input list. Please run 'add-input' first.")
        return

    if input_apn_index is not None:
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo("Invalid input APN index.")
            return
        tasks = [(input_apn_index, apn_list[input_apn_index])]
    else:
        # All input APNs.
        tasks = [(idx, apn_dict) for idx, apn_dict in enumerate(apn_list)]

    max_workers = max_threads if max_threads else None
    result_map = {}

    # Concurrency with process-based executor.
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_list = [executor.submit(_compute_invariants_for_input_apn, t) for t in tasks]

        for future in concurrent.futures.as_completed(future_list):
            apn_index, updated_dict, success, error_msg = future.result()
            if not success:
                click.echo(error_msg, err=True)
                updated_dict = None
            result_map[apn_index] = updated_dict

    # Merge results.
    for idx, original_dict in enumerate(apn_list):
        if idx in result_map and result_map[idx] is not None:
            apn_list[idx] = result_map[idx]

    save_input_apns_and_matches(apn_list)

    if input_apn_index is not None:
        # A single input APN.
        updated_dict = apn_list[input_apn_index]
        updated_apn = APN(
            updated_dict["poly"],
            updated_dict["field_n"],
            updated_dict["irr_poly"]
        )
        updated_apn.invariants = updated_dict["invariants"]
        click.echo(format_generic_apn(updated_apn, f"INPUT_APN {input_apn_index}"))
        click.echo("-" * 100)
        click.echo(f"Finished computing all invariants for INPUT_APN {input_apn_index} (and saved updates).")

    else:
        # All input APNs.
        for idx, apn_dict in enumerate(apn_list):
            updated_apn = APN(
                apn_dict["poly"],
                apn_dict["field_n"],
                apn_dict["irr_poly"]
            )
            updated_apn.invariants = apn_dict["invariants"]
            click.echo(format_generic_apn(updated_apn, f"INPUT_APN {idx}"))
            click.echo("-" * 100)
        click.echo("Finished computing all invariants for all input APNs (and saved updates).")


def _compute_invariants_for_input_apn(task: Tuple[int, Dict[str, Any]]) -> Tuple[int, Dict[str, Any], bool, str]:
    # Concurrency helper for a single input APN.
    apn_index, apn_dictionary = task
    try:
        # Convert dict => APN object.
        input_apn = APN(
            apn_dictionary["poly"],
            apn_dictionary["field_n"],
            apn_dictionary["irr_poly"]
        )
        input_apn.invariants = apn_dictionary.get("invariants", {})

        compute_all_invariants(input_apn)

        apn_dictionary["invariants"] = input_apn.invariants
        return (apn_index, apn_dictionary, True, "")
    except Exception as error:
        return (apn_index, None, False, f"Error computing invariants: {error}")