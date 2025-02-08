import click
import ast
import json
from pathlib import Path
from typing import List
from user_input_parser import PolynomialParser
from storage.json_storage_utils import load_input_apns, save_input_apns
from apn_properties import compute_apn_properties
from apn_object import APN
from representations.truth_table_representation import TruthTableRepresentation
from cli_commands.cli_utils import format_generic_apn

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

    # Separate list to store newly added APNs.
    added_apns = []

    if field_n is None:
        click.echo("Error: --field-n is required.", err=True)
        return

    def compute_invariants_for_apn(apn: APN):
        try:
            apn_tt = apn.get_truth_table()
            tt = apn_tt.representation.truth_table
        except Exception as e:
            click.echo(f"Error converting APN to truth table: {e}", err=True)
            return

        from computations.rank.delta_rank import DeltaRankComputation
        from computations.rank.gamma_rank import GammaRankComputation
        from computations.spectra.od_differential_spectrum import ODDifferentialSpectrumComputation
        from computations.spectra.od_walsh_spectrum import ODWalshSpectrumComputation

        try:
            d_rank = DeltaRankComputation().compute_rank(apn_tt)
            apn.invariants["delta_rank"] = d_rank
        except Exception as e:
            click.echo(f"Error computing Delta Rank: {e}", err=True)
            apn.invariants["delta_rank"] = None

        try:
            g_rank = GammaRankComputation().compute_rank(apn_tt)
            apn.invariants["gamma_rank"] = g_rank
        except Exception as e:
            click.echo(f"Error computing Gamma Rank: {e}", err=True)
            apn.invariants["gamma_rank"] = None

        is_quad = apn.properties.get("is_quadratic", False)
        if is_quad:
            try:
                odds_res = ODDifferentialSpectrumComputation().compute_spectrum(apn_tt)
                apn.invariants["odds"] = {int(k): int(v) for k, v in odds_res.items()}
            except Exception as e:
                click.echo(f"Error computing OD Differential Spectrum: {e}", err=True)
                apn.invariants["odds"] = "non-quadratic"
            try:
                odws_res = ODWalshSpectrumComputation().compute_spectrum(apn_tt)
                apn.invariants["odws"] = {int(k): int(v) for k, v in odws_res.items()}
            except Exception as e:
                click.echo(f"Error computing OD Extended Walsh Spectrum: {e}", err=True)
                apn.invariants["odws"] = "non-quadratic"
        else:
            apn.invariants["odds"] = "non-quadratic"
            apn.invariants["odws"] = "non-quadratic"

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

        # If not a duplicate, then create the new APN.
        apn = parser.parse_univariate_polynomial(poly_tuples, field_n, irr_poly)
        compute_apn_properties(apn)
        compute_invariants_for_apn(apn)

        added_apns.append(apn)
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
            tt_repr = TruthTableRepresentation(tt_values)
            apn_tt = APN.from_representation(tt_repr, n_val, irr_poly)
            compute_apn_properties(apn_tt)
            compute_invariants_for_apn(apn_tt)

            # Unique key to check for duplicates.
            poly_tuples = apn_tt.representation.univariate_polynomial
            candidate_key = _create_poly_key(n_val, irr_poly, poly_tuples)
            if candidate_key in existing_keys:
                click.echo(f"Skipped adding .tt file polynomial from {fpath} (already in input_apns).")
                continue
            added_apns.append(apn_tt)
            existing_keys.add(candidate_key)
        except Exception as e:
            click.echo(f"Error reading .tt file {fpath}: {e}", err=True)
            return

    # Add newly added APNs to main list.
    apn_list.extend(added_apns)

    # Save the updated list to input_apns.json.
    save_input_apns(apn_list)

    # Formatted printout of the newly added APNs.
    if added_apns:
        click.echo("\nNewly Added APNs:")
        click.echo("-" * 100)
        for i, apn in enumerate(added_apns, start=1):
            click.echo(format_generic_apn(apn, f"APN {i}"))
            click.echo("-" * 100)

def _create_apn_key(apn: APN) -> str:
    # Create a unique key from the APN's field_n, irr_poly, and polynomial.
    field_n = apn.field_n
    irr_poly = apn.irr_poly
    poly_list = apn.representation.univariate_polynomial
    return _create_poly_key(field_n, irr_poly, poly_list)

def _create_poly_key(field_n: int, irr_poly: str, poly_list: list) -> str:
    sorted_poly = sorted(poly_list, key=lambda tup: (tup[1], tup[0]))
    key_obj = [field_n, irr_poly, sorted_poly]
    return json.dumps(key_obj)