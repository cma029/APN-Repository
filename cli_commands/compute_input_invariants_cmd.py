import click
import concurrent.futures
from typing import Tuple, Dict, Any
from storage.json_storage_utils import (
    load_input_apns_and_matches,
    save_input_apns_and_matches
)
from cli_commands.cli_utils import format_generic_apn
from apn_invariants import compute_all_invariants
from apn_object import APN


@click.command("compute-input-invariants")
@click.option("--index", "input_apn_index", default=None, type=int,
              help="Index of a single input APN to process.")
@click.option("--max-threads", "max_threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def compute_input_invariants_cli(input_apn_index, max_threads):
    # Computes all invariants for the input APNs (not their matches).
    apn_list = load_input_apns_and_matches()
    if not apn_list:
        click.echo("No APNs in input list. Please run 'add-input' first.")
        return

    if input_apn_index is not None:
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo(f"Invalid input APN index: {input_apn_index}.")
            return
        tasks = [(input_apn_index, apn_list[input_apn_index])]
    else:
        tasks = [(apn_index, apn_dict) for apn_index, apn_dict in enumerate(apn_list)]

    max_workers = max_threads or None
    result_map = {}

    # Concurrency with process-based executor.
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_list = [executor.submit(_compute_invariants_for_one_apn, task_item) for task_item in tasks]

        # New lines: show status for each completed job.
        total_count = len(future_list)
        completed_count = 0

        for future in concurrent.futures.as_completed(future_list):
            completed_count += 1
            click.echo(f"Completed job {completed_count} of {total_count}.")
            apn_idx, updated_dict = future.result()
            result_map[apn_idx] = updated_dict

    # Merge results.
    for apn_index, original_dict in enumerate(apn_list):
        if apn_index in result_map and result_map[apn_index] is not None:
            apn_list[apn_index] = result_map[apn_index]

    save_input_apns_and_matches(apn_list)

    if input_apn_index is not None:
        updated_dict = apn_list[input_apn_index]
        show_apn = _build_apn_for_print(updated_dict)
        click.echo(format_generic_apn(show_apn, f"INPUT_APN {input_apn_index}"))
        click.echo("-" * 100)
        click.echo(f"Finished computing all invariants for INPUT_APN {input_apn_index}.")
    else:
        for idx, item in enumerate(apn_list):
            show_apn = _build_apn_for_print(item)
            click.echo(format_generic_apn(show_apn, f"INPUT_APN {idx}"))
            click.echo("-" * 100)
        click.echo("Finished computing all invariants for all input APNs.")


def _compute_invariants_for_one_apn(task: Tuple[int, Dict[str, Any]]) -> Tuple[int, Dict[str, Any]]:
    apn_idx, apn_dict = task

    # Build polynomial-based if poly != [], if empty, then from_cached_tt.
    poly_data = apn_dict.get("poly", [])
    cached_tt = apn_dict.get("cached_tt", [])

    if poly_data:
        apn_obj = APN(poly_data, apn_dict["field_n"], apn_dict["irr_poly"])
        if cached_tt:
            apn_obj._cached_tt_list = cached_tt
    elif cached_tt:
        apn_obj = APN.from_cached_tt(
            cached_tt,
            apn_dict["field_n"],
            apn_dict["irr_poly"]
        )
    else:
        apn_obj = APN([], apn_dict["field_n"], apn_dict["irr_poly"])

    # Merge existing invariants.
    apn_obj.invariants = apn_dict.get("invariants", {})

    compute_all_invariants(apn_obj)

    apn_dict["invariants"] = apn_obj.invariants
    return (apn_idx, apn_dict)


def _build_apn_for_print(apn_dict: Dict[str, Any]) -> APN:
    poly_data = apn_dict.get("poly", [])
    cached_tt = apn_dict.get("cached_tt", [])

    if poly_data:
        show_apn = APN(poly_data, apn_dict["field_n"], apn_dict["irr_poly"])
        # Skip re-computing the Truth Table by set _cached_tt_list (if present).
        if cached_tt:
            show_apn._cached_tt_list = cached_tt
    elif cached_tt:
        show_apn = APN.from_cached_tt(cached_tt, apn_dict["field_n"], apn_dict["irr_poly"])
    else:
        show_apn = APN([], apn_dict["field_n"], apn_dict["irr_poly"])

    show_apn.invariants = apn_dict.get("invariants", {})
    return show_apn