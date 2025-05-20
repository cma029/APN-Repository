from __future__ import annotations
import click
from typing import List, Tuple
from vbf_object import VBF
from registry import REG
from cli_commands.cli_utils import build_vbf_from_dict
from storage.json_storage_utils import load_input_vbfs_and_matches, save_input_vbfs_and_matches
from cli_commands.equivalence_runner import run_equivalence_on_matches


@click.command("uni3to1")
@click.option("--index", "single_vbf_index", default=None, type=int,
              help="If specified, only check that single VBF in the file. Otherwise process all.")
@click.option("--max-threads", "max_threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def uni3to1_equivalence_cli(single_vbf_index, max_threads):
    # Checking 3-to-1 linear equivalence for the input vectorial Boolean functions (VBFs).
    input_vbf_list = load_input_vbfs_and_matches()
    if not input_vbf_list:
        click.echo("No input VBFs found in storage/input_vbfs_and_matches.json.")
        return

    aggregator_k_to_1 = REG.get("invariant", "k_to_1")

    # Ensure the k_to_1 property is computed on each VBF.
    for vbf_dictionary in input_vbf_list:
        vbf_object = build_vbf_from_dict(vbf_dictionary)
        if "k_to_1" not in vbf_object.invariants:
            aggregator_k_to_1(vbf_object)
        vbf_dictionary["invariants"] = vbf_object.invariants

    # If the user specified --index, we only process that single VBF dictionary.
    if single_vbf_index is not None:
        if single_vbf_index < 0 or single_vbf_index >= len(input_vbf_list):
            click.echo(f"Invalid --index {single_vbf_index}. Valid range is 0-{len(input_vbf_list) - 1}.")
            return
        chosen_vbf_dicts = [input_vbf_list[single_vbf_index]]
        chosen_indices = [single_vbf_index]
    else:
        chosen_vbf_dicts = input_vbf_list
        chosen_indices = list(range(len(input_vbf_list)))

    # Build concurrency tasks.
    concurrency_tasks: List[Tuple[int, int, VBF, VBF]] = []
    for offset_index, single_vbf_dictionary in enumerate(chosen_vbf_dicts):
        actual_index = chosen_indices[offset_index]
        # Check if input VBF is 3-to-1.
        if single_vbf_dictionary["invariants"].get("k_to_1") != "3-to-1":
            continue
        candidate_vbf_object = build_vbf_from_dict(single_vbf_dictionary)

        # Build tasks for each of its matches (for each match, also check if it's 3-to-1).
        for match_index, match_dictionary in enumerate(single_vbf_dictionary.get("matches", [])):
            if match_dictionary.get("invariants", {}).get("k_to_1") != "3-to-1":
                continue
            match_vbf_object = build_vbf_from_dict(match_dictionary)
            concurrency_tasks.append((actual_index, match_index, candidate_vbf_object, match_vbf_object))

    # Run concurrency. The eq_key="uni3to1" will map to Uniform3to1EquivalenceTest.
    updated_vbf_list = run_equivalence_on_matches(
        input_vbf_list=input_vbf_list,
        concurrency_tasks=concurrency_tasks,
        eq_key="uni3to1",
        max_workers=max_threads,
    )

    # Save the updated list back to file.
    save_input_vbfs_and_matches(updated_vbf_list)
    
    # Print a short summary.
    removed_count = len(input_vbf_list) - len(updated_vbf_list)
    remain_count = len(updated_vbf_list)
    click.echo(
        f"Finished 3-to-1 linear check: removed {removed_count} input vbf(s); "
        f"{remain_count} input vbf(s) remain.")