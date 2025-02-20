import click
import json
import concurrent.futures
from typing import List, Dict, Any, Tuple
from storage.json_storage_utils import load_input_apns_and_matches
from apn_invariants import compute_all_invariants
from apn_object import APN
import pandas as pd
from apn_storage_pandas import (
    load_apn_dataframe_for_field,
    save_apn_dataframe_for_field,
    is_duplicate_candidate
)

@click.command("store-input-apns")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def store_input_apns_cli(max_threads):
    # Loads APNs from input_apns_and_matches.json and tries to store each
    # APN in the Parquet 'database' via store_apn_pandas.
    apn_dicts = load_input_apns_and_matches()
    if not apn_dicts:
        click.echo("No APNs in input_apns_and_matches.json. Add some with 'add-input'.")
        return

    click.echo(f"Storing {len(apn_dicts)} APN(s) into the database.")

    indexed_tasks = [(idx, apn_d) for idx, apn_d in enumerate(apn_dicts)]
    row_results: List[Tuple[int, Dict[str, Any]]] = []
    max_workers = max_threads or None

    # Using concurrency to build database row for each APN (compute invariants, etc.).
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for apn_task in indexed_tasks:
            future_obj = executor.submit(_build_db_row_for_apn, apn_task)
            future_map[future_obj] = apn_task[0]

        for completed_future in concurrent.futures.as_completed(future_map):
            apn_index = future_map[completed_future]
            try:
                row_dict = completed_future.result()
                if row_dict:
                    row_results.append((apn_index, row_dict))
            except Exception as exc:
                click.echo(f"Error building row for APN #{apn_index}: {exc}", err=True)

    if not row_results:
        click.echo("No new rows. Could possibly be due to is_apn = False.")
        return

    row_results.sort(key=lambda x: x[0])

    field_n_values = {row_data[1]["field_n"] for row_data in row_results}
    if len(field_n_values) != 1:
        click.echo("Warning. More than one field_n in the database-.parquet-file.")
        pass
    field_n_value = list(field_n_values)[0]

    existing_dataframe = load_apn_dataframe_for_field(field_n_value)
    duplicates_skipped = 0
    accepted_rows = []

    # Check for duplicates in each row using is_duplicate_candidate.
    for (apn_index, row_dict) in row_results:
        poly_str = row_dict["poly"]
        poly_data = []
        if poly_str:
            try:
                poly_data = json.loads(poly_str)
            except:
                poly_data = []
        irr_poly_str = row_dict["irr_poly"]

        if is_duplicate_candidate(existing_dataframe, field_n_value, irr_poly_str, poly_data):
            click.echo(f"Skipped duplicate for APN #{apn_index}.")
            duplicates_skipped += 1
        else:
            accepted_rows.append(row_dict)
            # Append existing_dataframe to memory so next row check sees it.
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


def _build_db_row_for_apn(apn_index_and_dict: Tuple[int, Dict[str, Any]]) -> Dict[str, Any]:
    # Build or re-check APN. Compute invariants, and produce a database row.
    apn_index, input_apn_dict = apn_index_and_dict
    field_n = input_apn_dict["field_n"]
    irr_poly_str = input_apn_dict["irr_poly"]
    poly_data = input_apn_dict.get("poly", [])
    cached_truth_table = input_apn_dict.get("cached_tt", [])
    existing_invariants = input_apn_dict.get("invariants", {})

    if poly_data:
        apn_obj = APN(poly_data, field_n, irr_poly_str)
        if cached_truth_table:
            apn_obj._cached_tt_list = cached_truth_table
    elif cached_truth_table:
        apn_obj = APN.from_cached_tt(cached_truth_table, field_n, irr_poly_str)
    else:
        apn_obj = APN([], field_n, irr_poly_str)

    apn_obj.invariants = existing_invariants

    compute_all_invariants(apn_obj)

    if not apn_obj.invariants.get("is_apn", False):
        return None

    # Build the database row.
    row_dict = {}
    row_dict["field_n"] = field_n
    row_dict["poly"] = json.dumps(poly_data)
    row_dict["irr_poly"] = irr_poly_str

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