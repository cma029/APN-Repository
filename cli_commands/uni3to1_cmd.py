import click
from storage.json_storage_utils import load_input_apns_and_matches, save_input_apns_and_matches
from apn_object import APN
from typing import List, Dict, Any, Tuple
from cli_commands.equivalence_runner import run_equivalence_on_matches
from apn_invariants import compute_k_to_1
from cli_commands.cli_utils import build_apn_from_dict
from computations.equivalence.lin_eq_2x_uniform_3to1 import Uniform3to1EquivalenceTest

@click.command("uni3to1")
@click.option("--index", "input_apn_index", default=None, type=int,
              help="If specified, only check that single APN in the file. Otherwise process all.")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def uni3to1_equivalence_cli(input_apn_index, max_threads):
    # Command for checking 3-to-1 (triplicate) linear equivalence using nskal/tripeq's alg1.c.
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

    # Ensure 'k_to_1' is computed if missing.
    for offset, apn_dict in enumerate(chosen_apns):
        apn_obj = build_apn_from_dict(apn_dict)
        if "k_to_1" not in apn_obj.invariants or not apn_obj.invariants["k_to_1"]:
            compute_k_to_1(apn_obj)
            apn_dict["invariants"] = apn_obj.invariants

    save_input_apns_and_matches(input_apn_list)


    # Build concurrency tasks only for APNs (and matches) with k_to_1 == "3-to-1".
    concurrency_tasks = _build_3to1_concurrency_tasks(chosen_apns, chosen_indices)

    # Run concurrency-based equivalence test.
    updated_apn_list = run_equivalence_on_matches(
        input_apn_list=input_apn_list,
        concurrency_tasks=concurrency_tasks,
        equivalence_worker_fn=_3to1_worker,
        eq_type_str="uni3to1-lin-eq",
        max_workers=max_threads
    )

    save_input_apns_and_matches(updated_apn_list)

    removed_count = len(input_apn_list) - len(updated_apn_list)
    remain_count = len(updated_apn_list)

    if removed_count > 0:
        click.echo(
            f"{removed_count} input APN(s) found 3-to-1 linear equivalence and are removed from file.")
    else:
        click.echo("No 3-to-1 equivalences found (or error has occurred).")

    click.echo(f"{remain_count} input APNs remain in storage/input_apns_and_matches.json.")


def _build_3to1_concurrency_tasks(chosen_apns: List[Dict[str, Any]],
                                  chosen_indices: List[int]) -> List[Tuple[int, int, APN, APN]]:
    # Builds concurrency tasks for 3-to-1 linear equivalence.
    tasks = []
    for offset_index, apn_dict in enumerate(chosen_apns):
        apn_index = chosen_indices[offset_index]

        input_apn_object = APN(
            apn_dict["poly"],
            apn_dict["field_n"],
            apn_dict["irr_poly"]
        )
        input_apn_object.invariants = apn_dict.get("invariants", {})

        # Need to have k_to_1 == '3-to-1'
        if input_apn_object.invariants.get("k_to_1", "") != "3-to-1":
            continue

        match_list = apn_dict.get("matches", [])
        for match_index, match_dict in enumerate(match_list):
            match_apn_object = APN(
                match_dict["poly"],
                match_dict["field_n"],
                match_dict["irr_poly"]
            )
            match_apn_object.invariants = match_dict.get("invariants", {})

            if match_apn_object.invariants.get("k_to_1", "") != "3-to-1":
                continue

            # Simple field n dimension check for safety.
            if input_apn_object.field_n != match_apn_object.field_n:
                continue

            tasks.append((apn_index, match_index, input_apn_object, match_apn_object))

    return tasks


def _3to1_worker(task_data: Tuple[int, int, APN, APN]) -> bool:
    # Returns True, False, or None if error.
    apn_idx, match_idx, input_apn, match_apn = task_data
    try:
        eq_tester = Uniform3to1EquivalenceTest()
        return eq_tester.are_equivalent(input_apn, match_apn)
    except Exception:
        return None