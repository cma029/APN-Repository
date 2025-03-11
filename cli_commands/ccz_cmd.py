import click
from typing import Dict, Any, List, Tuple
from apn_object import APN
from computations.equivalence.ccz_equivalence import CCZEquivalenceTest
from representations.truth_table_representation import TruthTableRepresentation
from storage.json_storage_utils import load_input_apns_and_matches, save_input_apns_and_matches
from cli_commands.equivalence_runner import run_equivalence_on_matches

@click.command("ccz")
@click.option("--index", "input_apn_index", default=None, type=int,
              help="If specified, only check the matches of that single input APN.")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def ccz_equivalence_cli(input_apn_index, max_threads):
    # Checks CCZ equivalence for the input APNs listed in input_apns_and_matches.json.
    input_apn_list = load_input_apns_and_matches()
    if not input_apn_list:
        click.echo("No input APNs found in storage/input_apns_and_matches.json.")
        return

    # Determine which APNs to process.
    if input_apn_index is not None:
        if input_apn_index < 0 or input_apn_index >= len(input_apn_list):
            click.echo(f"Invalid input APN index {input_apn_index}.")
            return
        chosen_apns = [input_apn_list[input_apn_index]]
        chosen_indices = [input_apn_index]
    else:
        chosen_apns = input_apn_list
        chosen_indices = list(range(len(input_apn_list)))

    # Build and run concurrency tasks.
    concurrency_tasks = _build_ccz_concurrency_tasks(chosen_apns, chosen_indices)

    updated_apn_list = run_equivalence_on_matches(
        input_apn_list=input_apn_list,
        concurrency_tasks=concurrency_tasks,
        equivalence_worker_fn=_ccz_worker,
        eq_type_str="ccz",
        max_workers=max_threads
    )

    save_input_apns_and_matches(updated_apn_list)

    removed_count = len(input_apn_list) - len(updated_apn_list)
    remain_count = len(updated_apn_list)

    if removed_count > 0:
        click.echo(f"{removed_count} input APN(s) found CCZ-equivalent. Removed from storage and recorded.")
    else:
        click.echo("No CCZ equivalences found for the chosen APNs.")

    click.echo(f"{remain_count} input APNs remain in storage/input_apns_and_matches.json.")


def _build_ccz_concurrency_tasks(chosen_apns: List[Dict[str, Any]], chosen_indices: List[int]) -> List[Tuple[int, int, Any]]:
    concurrency_tasks = []
    for offset_index, apn_dict in enumerate(chosen_apns):
        apn_index = chosen_indices[offset_index]

        # Build the input APN object and get its truth table.
        input_apn_object = APN(
            apn_dict["poly"],
            apn_dict["field_n"],
            apn_dict["irr_poly"]
        )
        input_apn_object.invariants = apn_dict.get("invariants", {})
        input_field_n = input_apn_object.field_n

        # Build tasks for each match in this APNs matches list.
        match_list = apn_dict.get("matches", [])
        for match_index, match_dict in enumerate(match_list):
            match_apn_object = APN(
                match_dict["poly"],
                match_dict["field_n"],
                match_dict["irr_poly"]
            )
            match_apn_object.invariants = match_dict.get("invariants", {})
            if input_field_n != match_apn_object.field_n:
                continue

            concurrency_tasks.append((apn_index, match_index, input_apn_object, match_apn_object))

    return concurrency_tasks


def _ccz_worker(task_data: Tuple[int, int, APN, APN]) -> bool:
    """
    Concurrency worker returns:
       True => equal.
       False => not equal.
       None => error has occurred.
    """
    apn_idx, match_idx, in_apn, mt_apn = task_data
    try:
        eq_tester = CCZEquivalenceTest()
        return eq_tester.are_equivalent(in_apn, mt_apn)
    except Exception:
        return None