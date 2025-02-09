import click
import ast
import json
import concurrent.futures
from pathlib import Path
from typing import List
from user_input_parser import PolynomialParser
from storage.json_storage_utils import load_input_apns, save_input_apns
from apn_properties import compute_apn_properties
from cli_commands.invariants_utils import compute_apn_invariants
from apn_object import APN
from representations.truth_table_representation import TruthTableRepresentation
from cli_commands.cli_utils import format_generic_apn

def compute_parallel(apn_data):
    apn, idx = apn_data
    try:
        compute_apn_properties(apn)
        compute_apn_invariants(apn)
        return (idx, apn, None)  # None is for no error.
    except Exception as e:
        return (idx, None, f"Error computing properties/invariants: {e}")

@click.command("add-input")
@click.option("--poly", "-p", multiple=True)
@click.option("--poly-file", type=click.Path(exists=True), multiple=True)
@click.option("--field-n", default=None, type=int)
@click.option("--irr-poly", default="", type=str)
def add_input_cli(poly, poly_file, field_n, irr_poly):
    # Adds user-specified univariate polynomial or .tt files to input_apns.json. 
    apn_list = load_input_apns()
    parser = PolynomialParser()

    # Create a set of existing keys so we can skip duplicates
    existing_keys = set(_create_apn_key(apn) for apn in apn_list)

    # Separate list to store newly added APNs (before concurrency).
    precomputed_apns = []

    if field_n is None:
        click.echo("Error: --field-n is required.", err=True)
        return

    # Univariate polynomials as input.
    for poly_str in poly:
        try:
            poly_tuples = ast.literal_eval(poly_str)
        except Exception as e:
            click.echo(f"Error parsing user polynomial {poly_str}: {e}", err=True)
            return

        # Unique key to check for duplicates.
        candidate_key = _create_poly_key(field_n, irr_poly, poly_tuples)
        if candidate_key in existing_keys:
            click.echo(f"Skipped adding polynomial {poly_str} (already in input_apns).")
            continue  # Skip duplicates

        try:
            apn = parser.parse_univariate_polynomial(poly_tuples, field_n, irr_poly)
        except Exception as e:
            click.echo(f"Error building APN from polynomial {poly_str}: {e}", err=True)
            continue

        precomputed_apns.append(apn)
        existing_keys.add(candidate_key)

    # Input from .tt files
    for fpath in poly_file:
        p = Path(fpath)
        if not p.is_file():
            click.echo(f"Error: File {fpath} not found.", err=True)
            return
        try:
            lines = p.read_text().splitlines()
            if len(lines) < 2:
                click.echo(f"File {fpath} does not have enough lines.", err=True)
                return
            n_val = int(lines[0].strip())
            tt_values = list(map(int, lines[1].strip().split()))
            expected_len = 1 << n_val
            if len(tt_values) != expected_len:
                click.echo(f"Incorrect TT length in {fpath}, expected {expected_len}, got {len(tt_values)}", err=True)
                return

            # Build the APN immediately in the main thread.
            apn_tt = APN.from_representation(
                TruthTableRepresentation(tt_values),
                n_val,
                irr_poly
            )

            # Unique key to check for duplicates.
            poly_tuples = apn_tt.representation.univariate_polynomial
            candidate_key = _create_poly_key(n_val, irr_poly, poly_tuples)
            if candidate_key in existing_keys:
                click.echo(f"Skipped adding .tt file polynomial from {fpath} (already in input_apns).")
                continue
            precomputed_apns.append(apn_tt)
            existing_keys.add(candidate_key)
        except Exception as e:
            click.echo(f"Error reading .tt file {fpath}: {e}", err=True)
            return

    # Store APNs in an enumerated list to preserve final order.
    tasks_for_pool = [(apn, i) for i, apn in enumerate(precomputed_apns)]
    results = [None]*len(tasks_for_pool)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        future_map = {executor.submit(compute_parallel, t): t[1] for t in tasks_for_pool}

        for fut in concurrent.futures.as_completed(future_map):
            index_in_list = future_map[fut]
            try:
                idx, apn_or_none, err = fut.result()
                if err:
                    click.echo(err, err=True)
                    results[idx] = None
                else:
                    results[idx] = apn_or_none
            except Exception as e:
                click.echo(f"Concurrency error: {e}", err=True)
                results[index_in_list] = None

    # Filter out the None's.
    final_apns = [r for r in results if r is not None]

    apn_list.extend(final_apns)
    save_input_apns(apn_list)

    # Formatted printout of the newly added APNs.
    if final_apns:
        click.echo("\nNewly Added APNs:")
        click.echo("-" * 100)
        for i, apn in enumerate(final_apns, start=1):
            click.echo(format_generic_apn(apn, f"APN {i}"))
            click.echo("-" * 100)

def _create_apn_key(apn: APN) -> str:
    field_n = apn.field_n
    irr_poly = apn.irr_poly
    poly_list = apn.representation.univariate_polynomial
    return _create_poly_key(field_n, irr_poly, poly_list)

def _create_poly_key(field_n: int, irr_poly: str, poly_list: list) -> str:
    sorted_poly = sorted(poly_list, key=lambda tup: (tup[1], tup[0]))
    key_obj = [field_n, irr_poly, sorted_poly]
    return json.dumps(key_obj)