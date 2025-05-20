import click
import json
import concurrent.futures
from typing import Tuple, List, Dict, Any
from storage.json_storage_utils import (
    load_input_vbfs_and_matches,
    save_input_vbfs_and_matches,
)
from storage_pandas import load_objects_for_dimension_pandas
from cli_commands.cli_utils import build_vbf_from_dict, get_custom_ordered_invariant_keys
from registry import REG

# Build a global registry dictionary from the callables.
_ALL_INVARIANT_FUNCTIONS: Dict[str, Any] = {}
for key in REG.keys("invariant"):
    _ALL_INVARIANT_FUNCTIONS[key] = REG.get("invariant", key)


@click.command("compare")
@click.option("--type", "user_requested_key", 
              type=click.Choice(get_custom_ordered_invariant_keys()),
              default="all", help="Which invariant(s) to compare. 'all' means every registered invariant.")
@click.option("--max-threads", "max_threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def compare_cli(user_requested_key: str, max_threads: int | None) -> None:
    """
    Compare invariants of input Vectorial Boolean Functions (VBFs) with the
    database VBFs for GF(2^n). The user picks a single invariant or "all".
    """
    input_vbf_list = load_input_vbfs_and_matches()
    if not input_vbf_list:
        click.echo("No input VBFs found. Please run 'add-input' first.")
        return

    # Enforce dimension consistency from the first VBF in storage.
    dimension_n = input_vbf_list[0].get("field_n", None)
    if dimension_n is None:
        click.echo("Error: The first VBF in storage does not have a valid field_n dimension.")
        return

    for idx, vbf_dict in enumerate(input_vbf_list):
        if vbf_dict.get("field_n") != dimension_n:
            click.echo(f"Error: VBF at index {idx} has dimension {vbf_dict.get('field_n')} "
                       f"which differs from {dimension_n}.")
            return

    # Load the database VBFs for dimension_n.
    db_vbf_list = load_objects_for_dimension_pandas(dimension_n)
    if not db_vbf_list:
        click.echo(f"No VBFs found in the database for GF(2^{dimension_n}).")
        return
    

    # If an VBF is stored with "is_apn" == True, we set "diff_uni" = 2.
    for db_vbf_object in db_vbf_list:
        if db_vbf_object.invariants.get("is_apn") is True:
            db_vbf_object.invariants["diff_uni"] = 2

    # Determine which invariants to compare.
    if user_requested_key == "all":
        user_invariants = list(_ALL_INVARIANT_FUNCTIONS.keys())
    else:
        user_invariants = [user_requested_key]

    # Gather the invariants that actually exist in the database.
    db_invariant_keys = set()
    for db_vbf in db_vbf_list:
        db_invariant_keys.update(db_vbf.invariants.keys())

    feasible_invariants = set(user_invariants).intersection(db_invariant_keys)
    if not feasible_invariants:
        click.echo("None of the requested invariants exist in the database. Skipping compare.")
        return

    final_invariant_list = list(feasible_invariants)

    # Compute missing invariants for each input VBF (in parallel).
    concurrency_tasks = [(idx, vbf_dict, final_invariant_list) 
                         for idx, vbf_dict in enumerate(input_vbf_list)]
    updated_dict_map: Dict[int, Dict[str, Any]] = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_threads) as executor:
        future_map = {executor.submit(_ensure_invariants_for_input_vbf, task): task[0]
                      for task in concurrency_tasks}
        for done_future in concurrent.futures.as_completed(future_map):
            idx_value = future_map[done_future]
            updated_dict_map[idx_value] = done_future.result()

    # Merge concurrency results.
    for idx, new_dict in updated_dict_map.items():
        input_vbf_list[idx] = new_dict

    # For each input VBF: first-time full search or narrow existing matches.
    for vbf_index, input_vbf_dict in enumerate(input_vbf_list):
        if input_vbf_dict.get("no_more_matches") is True:
            continue

        existing_matches = input_vbf_dict.get("matches", None)
        input_invariants = input_vbf_dict.get("invariants", {})

        if not existing_matches:
            # Full database search (if no matches exist yet).
            fresh_matches = []
            for db_object in db_vbf_list:
                if db_object.field_n != input_vbf_dict["field_n"]:
                    continue

                db_invariants = db_object.invariants
                if _compare_vbf_invariants(input_invariants, db_invariants, final_invariant_list):
                    fresh_matches.append({
                        "poly": db_object.representation.univariate_polynomial,
                        "field_n": db_object.field_n,
                        "irr_poly": db_object.irr_poly,
                        "invariants": db_object.invariants,
                        "compare_types": list(final_invariant_list),
                    })

            input_vbf_dict["matches"] = fresh_matches
            if not fresh_matches:
                input_vbf_dict["no_more_matches"] = True
        else:
            # Narrow existing matches.
            narrowed_list = []
            for match_item in existing_matches:
                db_invariants = match_item.get("invariants", {})
                if _compare_vbf_invariants(input_invariants, db_invariants, final_invariant_list):
                    old_types = match_item.get("compare_types", [])
                    new_types = set(old_types).union(final_invariant_list)
                    match_item["compare_types"] = list(new_types)
                    narrowed_list.append(match_item)

            input_vbf_dict["matches"] = narrowed_list
            if not narrowed_list:
                input_vbf_dict["no_more_matches"] = True

    # Save results and print summary.
    save_input_vbfs_and_matches(input_vbf_list)
    for idx, final_item in enumerate(input_vbf_list):
        match_count = len(final_item.get("matches", []))
        click.echo(f"For INPUT VBF {idx}, found {match_count} matches "
                   f"after comparing by '{user_requested_key}'.")
    click.echo("Done compare.")


def _compare_vbf_invariants(input_invariant: Dict[str, Any], db_invariant: Dict[str, Any], 
                            needed_keys: List[str]) -> bool:
    # Compare the chosen invariants.
    def _try_int(x):
        try:
            return int(x)
        except:
            return x

    def _parse_spectrum(value):
        if value == "non-quadratic":
            return "non-quadratic"
        if isinstance(value, dict):
            return {int(key): int(val) for key, val in value.items()}
        if isinstance(value, str) and value.startswith("{"):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return {int(key): int(val) for key, val in parsed.items()}
                return parsed
            except:
                return value
        return value

    for key in needed_keys:
        if key not in input_invariant or key not in db_invariant:
            return False
        input_value = input_invariant[key]
        db_value = db_invariant[key]

        # Special handling for ODDS/ODWS.
        if key in ("odds", "odws"):
            if _parse_spectrum(input_value) != _parse_spectrum(db_value):
                return False
        else:
            if _try_int(input_value) != _try_int(db_value):
                return False 
    
    return True


def _ensure_invariants_for_input_vbf(task: Tuple[int, Dict[str, Any], List[str]]) -> Dict[str, Any]:
    index_value, vbf_dictionary, invariant_keys_needed = task

    try:
        vbf_object = build_vbf_from_dict(vbf_dictionary)
        for key in invariant_keys_needed:
            if key not in vbf_object.invariants:
                aggregator_function = _ALL_INVARIANT_FUNCTIONS.get(key)
                if aggregator_function:
                    aggregator_function(vbf_object)

        # If success: store the updated invariants.
        vbf_dictionary["invariants"] = vbf_object.invariants

    except Exception as error:
        print(f"[ERROR in worker] index={index_value}, error={error}")

    return vbf_dictionary