import click
import ast
import json
import concurrent.futures
from pathlib import Path
from typing import List
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
@click.option("--field-n", default=None, type=int, required=True)
@click.option("--irr-poly", default="", type=str)
@click.option("--max-threads", default=None, type=int,
              help="Limit the number of parallel processes used. Default uses all available cores.")
def add_input_cli(poly, poly_file, field_n, irr_poly, max_threads):
    # Adds user-specified univariate polynomial or .tt files to input_apns_and_matches.json.
    parser = PolynomialParser()

    # Load existing data.
    apn_list = load_input_apns_and_matches()

    # Build a set of existing keys so we can skip duplicates.
    existing_keys = set()
    for apn_dict in apn_list:
        k = _create_poly_key(
            apn_dict["poly"], 
            apn_dict["field_n"], 
            apn_dict["irr_poly"]
        )
        existing_keys.add(k)

    new_apns = []

    # Univariate polynomials as input.
    for poly_str in poly:
        try:
            poly_tuples = ast.literal_eval(poly_str)
        except Exception as e:
            click.echo(f"Error parsing user polynomial {poly_str}: {e}", err=True)
            continue

        # Unique key to check for duplicates. If APN already exist in the file, skip.
        candidate_key = _create_poly_key(poly_tuples, field_n, irr_poly)
        if candidate_key in existing_keys:
            click.echo(f"Skipped duplicate polynomial {poly_str} (already in file).")
            continue

        apn_obj = parser.parse_univariate_polynomial(poly_tuples, field_n, irr_poly)
        new_apns.append(apn_obj)
        existing_keys.add(candidate_key)

    # Input from .tt files
    for fpath in poly_file:
        p = Path(fpath)
        if not p.is_file():
            click.echo(f"Error: File {fpath} not found.", err=True)
            continue
        try:
            lines = p.read_text().splitlines()
            if len(lines) < 2:
                click.echo(f"File {fpath} missing lines.", err=True)
                continue
            n_val = int(lines[0].strip())
            tt_values = list(map(int, lines[1].strip().split()))
            if len(tt_values) != (1 << n_val):
                click.echo(f"Incorrect TT length for {fpath}.", err=True)
                continue

            # Unique key to check for duplicates. If APN already exist in the file, skip.
            candidate_key = _create_poly_key([("TT", sum(tt_values))], n_val, irr_poly)
            if candidate_key in existing_keys:
                click.echo(f"Skipped duplicate TT from {fpath} (already in file).")
                continue

            from_truth = APN.from_representation(
                TruthTableRepresentation(tt_values), 
                n_val, 
                irr_poly
            )
            new_apns.append(from_truth)
            existing_keys.add(candidate_key)
        except Exception as e:
            click.echo(f"Error reading .tt file {fpath}: {e}", err=True)

    if not new_apns:
        click.echo("No new APNs were added.")
        return

    # Concurrent Differential Uniformity check: is_apn. If not APN, we skip it.
    tasks = [(i, apn) for i, apn in enumerate(new_apns)]
    max_workers = max_threads if max_threads else None
    results_map = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futs = [executor.submit(_check_task, t) for t in tasks]
        for fut in concurrent.futures.as_completed(futs):
            iidx, updated_apn = fut.result()
            results_map[iidx] = updated_apn

    # Filter out non-APN.
    final_added_apns = []
    for i in range(len(new_apns)):
        apn_ = results_map.get(i)
        if apn_ and apn_.invariants.get("is_apn", False):
            final_added_apns.append(apn_)

    if not final_added_apns:
        click.echo("The new APNs are actually not APNs (differential uniformity != 2).")
        return

    new_entries = []
    for apn_ in final_added_apns:
        entry = {
            "poly": apn_.representation.univariate_polynomial,
            "field_n": apn_.field_n,
            "irr_poly": apn_.irr_poly,
            "invariants": apn_.invariants,
            "matches": []
        }
        new_entries.append(entry)

    apn_list.extend(new_entries)
    save_input_apns_and_matches(apn_list)

    # Print newly added APNs with format_generic_apn.
    if new_entries:
        click.echo("\nNewly Added APNs:")
        click.echo("-" * 100)
        for i, entry in enumerate(new_entries, start=1):
            added_apn = APN(entry["poly"], entry["field_n"], entry["irr_poly"])
            added_apn.invariants = entry["invariants"]
            click.echo(format_generic_apn(added_apn, f"APN {i}"))
            click.echo("-" * 100)


def _check_task(task):
    # Top-level function for concurrency to avoid pickling issues.
    iidx, apn_ = task
    compute_is_apn(apn_)
    return (iidx, apn_)


def _create_poly_key(poly_list, field_n, irr_poly):
    try:
        # If poly_list is a list of (coefficient_exp, monomial_exp), we sort them.
        sorted_poly = sorted(poly_list, key=lambda x: (x[0], x[1]))
        key_obj = [field_n, irr_poly, sorted_poly]
    except:
        # Fallback:
        key_obj = [field_n, irr_poly, poly_list]

    return json.dumps(key_obj, sort_keys=True)