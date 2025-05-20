import click
import concurrent.futures
from typing import Tuple, Dict, Any
from storage.json_storage_utils import (
    load_input_vbfs_and_matches,
    save_input_vbfs_and_matches
)
from cli_commands.cli_utils import format_generic_vbf, build_vbf_from_dict
from invariants import compute_all_invariants
from vbf_object import VBF


@click.command("compute-input-invariants")
@click.option("--index", "input_vbf_index", default=None, type=int,
              help="Index of a single input VBF to process.")
@click.option("--max-threads", "max_threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def compute_input_invariants_cli(input_vbf_index, max_threads):
    # Computes all invariants for the input VBFs (not their matches).
    vbf_list = load_input_vbfs_and_matches()
    if not vbf_list:
        click.echo("No VBFs in input list. Please run 'add-input' first.")
        return

    if input_vbf_index is not None:
        if input_vbf_index < 0 or input_vbf_index >= len(vbf_list):
            click.echo(f"Invalid input VBF index: {input_vbf_index}.")
            return
        tasks = [(input_vbf_index, vbf_list[input_vbf_index])]
    else:
        tasks = [(vbf_index, vbf_dict) for vbf_index, vbf_dict in enumerate(vbf_list)]

    max_workers = max_threads or None
    result_map = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_list = [executor.submit(_compute_invariants_for_one_vbf, task_item) for task_item in tasks]

        # Show status for each completed job.
        total_count = len(future_list)
        completed_count = 0

        for future in concurrent.futures.as_completed(future_list):
            completed_count += 1
            click.echo(f"Completed job {completed_count} of {total_count}.")
            vbf_idx, updated_dict = future.result()
            result_map[vbf_idx] = updated_dict

    # Merge results into the main VBF list.
    for vbf_index in range(len(vbf_list)):
        if vbf_index in result_map and result_map[vbf_index] is not None:
            vbf_list[vbf_index] = result_map[vbf_index]

    save_input_vbfs_and_matches(vbf_list)

    if input_vbf_index is not None:
        updated_dict = vbf_list[input_vbf_index]
        show_vbf = build_vbf_from_dict(updated_dict)
        click.echo(format_generic_vbf(show_vbf, f"INPUT VBF {input_vbf_index}"))
        click.echo("-" * 100)
        click.echo(f"Finished computing all invariants for INPUT VBF {input_vbf_index}.")
    else:
        for idx, item in enumerate(vbf_list):
            show_vbf = build_vbf_from_dict(item)
            click.echo(format_generic_vbf(show_vbf, f"INPUT VBF {idx}"))
            click.echo("-" * 100)
        click.echo("Finished computing all invariants for all input VBFs.")


def _compute_invariants_for_one_vbf(task: Tuple[int, Dict[str, Any]]) -> Tuple[int, Dict[str, Any]]:
    vbf_idx, vbf_dict = task

    # Build polynomial-based if poly != [], otherwise from_cached_tt.
    poly_data = vbf_dict.get("poly", [])
    cached_tt = vbf_dict.get("cached_tt", [])

    if poly_data:
        vbf_object = VBF(poly_data, vbf_dict["field_n"], vbf_dict["irr_poly"])
        if cached_tt:
            vbf_object._cached_tt_list = cached_tt
    elif cached_tt:
        vbf_object = VBF.from_cached_tt(cached_tt, vbf_dict["field_n"], vbf_dict["irr_poly"])
    else:
        vbf_object = VBF([], vbf_dict["field_n"], vbf_dict["irr_poly"])

    # Merge existing invariants.
    vbf_object.invariants = vbf_dict.get("invariants", {})

    compute_all_invariants(vbf_object)

    vbf_dict["invariants"] = vbf_object.invariants
    return (vbf_idx, vbf_dict)