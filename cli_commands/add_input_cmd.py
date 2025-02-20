import click
import ast
import json
import concurrent.futures
from pathlib import Path
from user_input_parser import PolynomialParser
from storage.json_storage_utils import (
    load_input_apns_and_matches,
    save_input_apns_and_matches
)
from apn_object import APN
from representations.truth_table_representation import TruthTableRepresentation
from cli_commands.cli_utils import format_generic_apn
from apn_invariants import compute_is_apn


@click.command("add-input")
@click.option("--poly", "-p", multiple=True, help="Univariate Polynomial in the form [(0,3), (1,9), ...]")
@click.option("--poly-file", type=click.Path(exists=True), multiple=True,
              help="Truth Table file (.tt) with 'n' on the first line and the Truth Table on the second.")
@click.option("--field-n", default=None, type=int, required=True, help="GF(2^n) dimension (n).")
@click.option("--irr-poly", default="", type=str,
              help="Irreducible polynomial string, e.g. 'x^6 + x^4 + x^3 + x + 1'")
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def add_input_cli(poly, poly_file, field_n, irr_poly, max_threads):
    # Adds user-specified univariate polynomial or .tt files to input_apns_and_matches.json.
    parser = PolynomialParser()

    # Load existing data.
    apn_list = load_input_apns_and_matches()

    # Track existing keys so we can skip duplicates.
    existing_keys = set()
    for existing_apn_dict in apn_list:
        existing_key = _create_poly_key(
            existing_apn_dict["poly"],
            existing_apn_dict["field_n"],
            existing_apn_dict["irr_poly"]
        )
        existing_keys.add(existing_key)

    new_apns = []

    # Univariate polynomials as input.
    for poly_str in poly:
        try:
            poly_tuples = ast.literal_eval(poly_str)
        except Exception as parse_exc:
            click.echo(f"Error parsing user polynomial '{poly_str}': {parse_exc}", err=True)
            continue

        candidate_key = _create_poly_key(poly_tuples, field_n, irr_poly)
        if candidate_key in existing_keys:
            click.echo(f"Skipped duplicate polynomial {poly_str} (already in file).")
            continue
        # Build an APN from the polynomial based representation.
        apn_obj = APN(poly_tuples, field_n, irr_poly)
        new_apns.append(apn_obj)
        existing_keys.add(candidate_key)

    # Input from .tt files
    for tt_filepath_str in poly_file:
        file_path_obj = Path(tt_filepath_str)
        if not file_path_obj.is_file():
            click.echo(f"Error: File '{tt_filepath_str}' not found.", err=True)
            continue
        lines = file_path_obj.read_text().splitlines()
        if len(lines) < 2:
            click.echo(f"File '{tt_filepath_str}' missing lines.", err=True)
            continue
        n_val = int(lines[0].strip())
        tt_values = list(map(int, lines[1].strip().split()))
        if len(tt_values) != (1 << n_val):
            click.echo(f"Wrong Truth Table length for '{tt_filepath_str}'.", err=True)
            continue

        candidate_key = _create_poly_key([("TT", sum(tt_values))], n_val, irr_poly)
        if candidate_key in existing_keys:
            click.echo(f"Skipped duplicate Truth Table from {tt_filepath_str} (already in file).")
            continue

        # Build APN from the Truth Table based representation.
        tt_apn = APN.from_representation(
            TruthTableRepresentation(tt_values),
            n_val,
            irr_poly
        )
        new_apns.append(tt_apn)
        existing_keys.add(candidate_key)

    if not new_apns:
        click.echo("No new APNs were added.")
        return

    # Concurrent Differential Uniformity check: is_apn. If not APN, we skip the APN.
    tasks = [(idx_val, apn_obj) for idx_val, apn_obj in enumerate(new_apns)]
    max_workers = max_threads or None
    results_map = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_list = [executor.submit(_compute_is_apn_task, single_task) for single_task in tasks]
        for done_future in concurrent.futures.as_completed(future_list):
            idx_val, updated_apn_obj = done_future.result()
            results_map[idx_val] = updated_apn_obj

    # Filter out non-APN.
    final_added_apns = []
    for idx_val in range(len(new_apns)):
        updated_apn_obj = results_map.get(idx_val)
        if updated_apn_obj and updated_apn_obj.invariants.get("is_apn", False):
            final_added_apns.append(updated_apn_obj)

    if not final_added_apns:
        click.echo("The new APNs are actually not APNs (differential uniformity != 2).")
        return

    new_entries = []
    for final_apn_obj in final_added_apns:
        if hasattr(final_apn_obj.representation, "univariate_polynomial"):
            stored_poly = final_apn_obj.representation.univariate_polynomial
        else:
            stored_poly = []

        cached_tt_list = final_apn_obj._get_truth_table_list()

        entry_dict = {
            "poly": stored_poly,
            "field_n": final_apn_obj.field_n,
            "irr_poly": final_apn_obj.irr_poly,
            "invariants": final_apn_obj.invariants,
            "matches": [],
            "cached_tt": cached_tt_list
        }
        new_entries.append(entry_dict)

    apn_list.extend(new_entries)
    save_input_apns_and_matches(apn_list)

    # Print newly added APNs with format_generic_apn.
    if new_entries:
        click.echo("\nNewly Added APNs:")
        click.echo("-" * 100)
        for index_added, entry_dict in enumerate(new_entries, start=1):
            if entry_dict["poly"]:
                # We want polynomial based representation.
                show_apn = APN(entry_dict["poly"], entry_dict["field_n"], entry_dict["irr_poly"])
            else:
                # If there is no polynomial, then it is Truth Table based.
                show_apn = APN.from_representation(
                    TruthTableRepresentation(entry_dict["cached_tt"]),
                    entry_dict["field_n"],
                    entry_dict["irr_poly"]
                )

            show_apn.invariants = entry_dict["invariants"]
            click.echo(format_generic_apn(show_apn, f"APN {index_added}"))
            click.echo("-" * 100)


def _compute_is_apn_task(task):
    idx_val, apn_obj = task
    compute_is_apn(apn_obj)
    return (idx_val, apn_obj)

def _create_poly_key(poly_list, field_n, irr_poly):
    try:
        # If poly_list is a list of (coefficient_exp, monomial_exp), we sort them.
        sorted_poly = sorted(poly_list, key=lambda poly_tup: (poly_tup[0], poly_tup[1]))
        key_obj = [field_n, irr_poly, sorted_poly]
    except:
        # Fallback:
        key_obj = [field_n, irr_poly, poly_list]
    return json.dumps(key_obj, sort_keys=True)