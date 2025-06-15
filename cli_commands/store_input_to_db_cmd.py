import click
import json
import concurrent.futures
from typing import List, Dict, Any, Tuple
from storage.json_storage_utils import load_input_vbfs_and_matches, save_input_vbfs_and_matches
from cli_commands.cli_utils import build_vbf_from_dict
from invariants import compute_all_invariants
import pandas as pd
from storage_pandas import (
    load_dataframe_for_dimension,
    save_dataframe_for_dimension,
    is_duplicate_candidate
)


@click.command("store-input")
@click.option("--index", default=None, type=int,
              help="Optionally store only the VBF at the specified index.")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def store_input_cli(index, max_threads):
    """
    Loads VBFs from storage/input_vbfs_and_matches.json, computes all used invariants,
    checks for duplicates and stores the new VBFs into the Parquet database.
    """
    vbf_dicts = load_input_vbfs_and_matches()
    if not vbf_dicts:
        click.echo("No VBFs in input_vbfs_and_matches.json. Add some with 'add-input'.")
        return

    # Validate index if specified.
    if index is not None:
        if index < 0 or index >= len(vbf_dicts):
            click.echo(f"Invalid VBF index: {index}.")
            return
        # Process just this one VBF.
        relevant_vbfs = [(index, vbf_dicts[index])]
    else:
        relevant_vbfs = [(idx, vbf_d) for idx, vbf_d in enumerate(vbf_dicts)]

    click.echo("Computing invariants for selected VBF(s)...")
    updated_map = {}

    max_workers = max_threads or None
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for (vbf_idx, vbf_dict) in relevant_vbfs:
            future_obj = executor.submit(_compute_invariants, (vbf_idx, vbf_dict))
            future_map[future_obj] = vbf_idx

        completed_count = 0
        for future in concurrent.futures.as_completed(future_map):
            vbf_idx_val = future_map[future]
            try:
                updated_dict = future.result()
                if updated_dict is not None:
                    updated_map[vbf_idx_val] = updated_dict
            except Exception as exc:
                click.echo(f"Error computing invariants for VBF #{vbf_idx_val}: {exc}", err=True)
            completed_count += 1
            click.echo(f"Computed invariants for {completed_count} of {len(relevant_vbfs)} VBF(s).")

    # Merge updated invariants back into the vbf_dicts.
    for (vbf_idx_val, new_dict) in updated_map.items():
        vbf_dicts[vbf_idx_val] = new_dict

    save_input_vbfs_and_matches(vbf_dicts)


    click.echo("Storing VBFs into the database (if they are valid and not duplicates)...")

    if index is not None:
        relevant_vbfs = [(index, vbf_dicts[index])]
    else:
        relevant_vbfs = [(idx, vbf_d) for idx, vbf_d in enumerate(vbf_dicts)]

    row_results: List[Tuple[int, Dict[str, Any]]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map_2 = {}
        for (vbf_idx, vbf_dict) in relevant_vbfs:
            future_obj = executor.submit(_build_db_row, (vbf_idx, vbf_dict))
            future_map_2[future_obj] = vbf_idx

        completed_count_2 = 0
        for done_future in concurrent.futures.as_completed(future_map_2):
            vbf_idx_val = future_map_2[done_future]
            try:
                row_dict = done_future.result()
                if row_dict:
                    row_results.append((vbf_idx_val, row_dict))
            except Exception as exc:
                click.echo(f"Error building row for VBF #{vbf_idx_val}: {exc}", err=True)
            completed_count_2 += 1
            click.echo(f"Stored row for {completed_count_2} of {len(relevant_vbfs)} VBF(s).")

    if not row_results:
        click.echo("No new rows. Possibly due to is_apn = False or other issues.")
        return

    # Sort results by original VBF index to keep ordering.
    row_results.sort(key=lambda x: x[0])

    # All VBFs must have the same field_n.
    field_n_values = {row_data[1]["field_n"] for row_data in row_results}
    if len(field_n_values) != 1:
        click.echo("Error: More than one field_n encountered among these VBFs => Aborting store.")
        return
    field_n_value = list(field_n_values)[0]

    existing_dataframe = load_dataframe_for_dimension(field_n_value, is_apn=True)
    duplicates_skipped = 0
    accepted_rows = []

    # Check for duplicates in each row using the is_duplicate_candidate.
    for (vbf_index_val, row_dict) in row_results:
        poly_str = row_dict["poly"]
        poly_data = []
        if poly_str:
            try:
                poly_data = json.loads(poly_str)
            except:
                poly_data = []
        irr_poly_str = row_dict["irr_poly"]

        if is_duplicate_candidate(existing_dataframe, field_n_value, irr_poly_str, poly_data):
            click.echo(f"Skipped duplicate for VBF #{vbf_index_val}.")
            duplicates_skipped += 1
        else:
            accepted_rows.append(row_dict)
            # Append to dataframe in memory so next row check sees it.
            existing_dataframe = pd.concat([existing_dataframe, pd.DataFrame([row_dict])], ignore_index=True)

    if not accepted_rows:
        click.echo("All new VBFs were duplicates => nothing new stored.")
        return

    final_dataframe = existing_dataframe.drop_duplicates()
    save_dataframe_for_dimension(field_n_value, final_dataframe, is_apn=True)
    stored_count = len(accepted_rows)

    click.echo(
        f"Done storing VBFs from input_vbfs_and_matches.json. "
        f"{stored_count} new VBF(s) stored, {duplicates_skipped} duplicate(s) skipped."
    )


def _compute_invariants(task: Tuple[int, Dict[str, Any]]) -> Dict[str, Any]:
    vbf_index, input_vbf_dict = task
    vbf_object = build_vbf_from_dict(input_vbf_dict)

    compute_all_invariants(vbf_object)

    # Write invariants back into the dictionary.
    input_vbf_dict["invariants"] = vbf_object.invariants

    # Returns None on any error.
    return input_vbf_dict


def _build_db_row(vbf_index_and_dict: Tuple[int, Dict[str, Any]]) -> Dict[str, Any]:
    # Build VBF and produce a database row for storing in the Parquet file.
    vbf_index, input_vbf_dict = vbf_index_and_dict
    vbf_object = build_vbf_from_dict(input_vbf_dict)

    if not vbf_object.invariants.get("is_apn", False):
        return None

    # Build the database row.
    row_dict = {}
    row_dict["field_n"] = vbf_object.field_n
    row_dict["poly"] = json.dumps(input_vbf_dict.get("poly", []))
    row_dict["irr_poly"] = vbf_object.irr_poly

    row_dict["odds"] = _jsonify_if_dict(vbf_object.invariants.get("odds", "non-quadratic"))
    row_dict["odws"] = _jsonify_if_dict(vbf_object.invariants.get("odws", "non-quadratic"))
    row_dict["delta_rank"] = vbf_object.invariants.get("delta_rank", None)
    row_dict["gamma_rank"] = vbf_object.invariants.get("gamma_rank", None)
    row_dict["algebraic_degree"] = vbf_object.invariants.get("algebraic_degree", None)
    row_dict["is_quadratic"] = vbf_object.invariants.get("is_quadratic", False)
    row_dict["is_apn"] = vbf_object.invariants.get("is_apn", False)
    row_dict["is_monomial"] = vbf_object.invariants.get("is_monomial", False)
    row_dict["k_to_1"] = vbf_object.invariants.get("k_to_1", "unknown")

    row_dict["citation"] = vbf_object.invariants.get("citation", f"No citation provided")
    return row_dict


def _jsonify_if_dict(value):
    import json
    if isinstance(value, dict):
        return json.dumps(value)
    return value