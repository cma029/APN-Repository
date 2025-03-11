import click
import json
import concurrent.futures
from typing import List, Dict, Any, Tuple
from storage.json_storage_utils import load_input_apns_and_matches, save_input_apns_and_matches
from cli_commands.cli_utils import build_apn_from_dict
from apn_invariants import compute_all_invariants
import pandas as pd
from apn_storage_pandas import (
    load_apn_dataframe_for_field,
    save_apn_dataframe_for_field,
    is_duplicate_candidate
)


@click.command("store-input")
@click.option("--index", default=None, type=int,
              help="Optionally store only the APN at the specified index.")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def store_input_apns_cli(index, max_threads):
    """
    Loads APNs from storage/input_apns_and_matches.json, computes all invariants,
    checks for duplicates and stores the new APNs into the Parquet database.
    """
    apn_dicts = load_input_apns_and_matches()
    if not apn_dicts:
        click.echo("No APNs in input_apns_and_matches.json. Add some with 'add-input'.")
        return

    # Validate index if specified.
    if index is not None:
        if index < 0 or index >= len(apn_dicts):
            click.echo(f"Invalid APN index: {index}.")
            return
        # Process just this one APN.
        relevant_apns = [(index, apn_dicts[index])]
    else:
        relevant_apns = [(idx, apn_d) for idx, apn_d in enumerate(apn_dicts)]

    click.echo("Computing invariants for selected APN(s)...")
    updated_map = {}

    max_workers = max_threads or None
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for (apn_idx, apn_dict) in relevant_apns:
            future_obj = executor.submit(_compute_invariants_for_apn, (apn_idx, apn_dict))
            future_map[future_obj] = apn_idx

        completed_count = 0
        for future in concurrent.futures.as_completed(future_map):
            apn_idx_val = future_map[future]
            try:
                updated_dict = future.result()
                if updated_dict is not None:
                    updated_map[apn_idx_val] = updated_dict
            except Exception as e:
                click.echo(f"Error computing invariants for APN #{apn_idx_val}: {e}", err=True)
            completed_count += 1
            click.echo(f"Computed invariants for {completed_count} of {len(relevant_apns)} APN(s).")

    # Merge updated invariants back into the apn_dicts.
    for (apn_idx_val, new_dict) in updated_map.items():
        apn_dicts[apn_idx_val] = new_dict

    save_input_apns_and_matches(apn_dicts)


    click.echo("Storing APNs into the database (if they are valid and not duplicates)...")

    if index is not None:
        relevant_apns = [(index, apn_dicts[index])]
    else:
        relevant_apns = [(idx, apn_d) for idx, apn_d in enumerate(apn_dicts)]

    row_results: List[Tuple[int, Dict[str, Any]]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map_2 = {}
        for (apn_idx, apn_dict) in relevant_apns:
            future_obj = executor.submit(_build_db_row_for_apn, (apn_idx, apn_dict))
            future_map_2[future_obj] = apn_idx

        completed_count_2 = 0
        for done_future in concurrent.futures.as_completed(future_map_2):
            apn_idx_val = future_map_2[done_future]
            try:
                row_dict = done_future.result()
                if row_dict:
                    row_results.append((apn_idx_val, row_dict))
            except Exception as exc:
                click.echo(f"Error building row for APN #{apn_idx_val}: {exc}", err=True)
            completed_count_2 += 1
            click.echo(f"Stored row for {completed_count_2} of {len(relevant_apns)} APN(s).")

    if not row_results:
        click.echo("No new rows. Possibly due to is_apn = False or other issues.")
        return

    # Sort results by original APN index to keep ordering.
    row_results.sort(key=lambda x: x[0])

    # All APNs must have the same field_n.
    field_n_values = {row_data[1]["field_n"] for row_data in row_results}
    if len(field_n_values) != 1:
        click.echo("Error: More than one field_n encountered among these APNs => Aborting store.")
        return
    field_n_value = list(field_n_values)[0]

    existing_dataframe = load_apn_dataframe_for_field(field_n_value)
    duplicates_skipped = 0
    accepted_rows = []

    # Check for duplicates in each row using the is_duplicate_candidate.
    for (apn_index_val, row_dict) in row_results:
        poly_str = row_dict["poly"]
        poly_data = []
        if poly_str:
            try:
                poly_data = json.loads(poly_str)
            except:
                poly_data = []
        irr_poly_str = row_dict["irr_poly"]

        if is_duplicate_candidate(existing_dataframe, field_n_value, irr_poly_str, poly_data):
            click.echo(f"Skipped duplicate for APN #{apn_index_val}.")
            duplicates_skipped += 1
        else:
            accepted_rows.append(row_dict)
            # Append to dataframe in memory so next row check sees it.
            existing_dataframe = pd.concat([existing_dataframe, pd.DataFrame([row_dict])], ignore_index=True)

    if not accepted_rows:
        click.echo("All new APNs were duplicates => nothing new stored.")
        return

    final_dataframe = existing_dataframe.drop_duplicates()
    save_apn_dataframe_for_field(field_n_value, final_dataframe)
    stored_count = len(accepted_rows)

    click.echo(
        f"Done storing APNs from input_apns_and_matches.json. "
        f"{stored_count} new APN(s) stored, {duplicates_skipped} duplicate(s) skipped."
    )


def _compute_invariants_for_apn(task: Tuple[int, Dict[str, Any]]) -> Dict[str, Any]:
    apn_index, input_apn_dict = task
    apn_obj = build_apn_from_dict(input_apn_dict)

    compute_all_invariants(apn_obj)

    # Write invariants back into the dictionary.
    input_apn_dict["invariants"] = apn_obj.invariants

    # Returns None on any error.
    return input_apn_dict


def _build_db_row_for_apn(apn_index_and_dict: Tuple[int, Dict[str, Any]]) -> Dict[str, Any]:
    # Build APN and produce a database row for storing in the Parquet file.
    apn_index, input_apn_dict = apn_index_and_dict
    apn_obj = build_apn_from_dict(input_apn_dict)

    if not apn_obj.invariants.get("is_apn", False):
        return None

    # Build the database row.
    row_dict = {}
    row_dict["field_n"] = apn_obj.field_n
    row_dict["poly"] = json.dumps(input_apn_dict.get("poly", []))
    row_dict["irr_poly"] = apn_obj.irr_poly

    row_dict["odds"] = _jsonify_if_dict(apn_obj.invariants.get("odds", "non-quadratic"))
    row_dict["odws"] = _jsonify_if_dict(apn_obj.invariants.get("odws", "non-quadratic"))
    row_dict["delta_rank"] = apn_obj.invariants.get("delta_rank", None)
    row_dict["gamma_rank"] = apn_obj.invariants.get("gamma_rank", None)
    row_dict["algebraic_degree"] = apn_obj.invariants.get("algebraic_degree", None)
    row_dict["is_quadratic"] = apn_obj.invariants.get("is_quadratic", False)
    row_dict["is_apn"] = apn_obj.invariants.get("is_apn", False)
    row_dict["is_monomial"] = apn_obj.invariants.get("is_monomial", False)
    row_dict["k_to_1"] = apn_obj.invariants.get("k_to_1", "unknown")

    row_dict["citation"] = apn_obj.invariants.get("citation", f"No citation for APN {apn_index}")
    return row_dict


def _jsonify_if_dict(value):
    import json
    if isinstance(value, dict):
        return json.dumps(value)
    return value