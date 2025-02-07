import click
import ast
from pathlib import Path
from typing import List
from user_input_parser import PolynomialParser
from storage.input_json_storage import load_input_apns, save_input_apns
from apn_properties import compute_apn_properties
from apn_object import APN
from representations.truth_table_representation import TruthTableRepresentation

@click.command("add-input")
@click.option("--poly", "-p", multiple=True)
@click.option("--poly-file", type=click.Path(exists=True), multiple=True)
@click.option("--field-n", default=None, type=int)
@click.option("--irr-poly", default="", type=str)
def add_input_cli(poly, poly_file, field_n, irr_poly):
    # Adds user-specified univariate polynomial or .tt files to input_apns.json. 
    apn_list = load_input_apns()
    parser = PolynomialParser()

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

        from computations.rank.gamma_rank import GammaRankComputation
        from computations.rank.delta_rank import DeltaRankComputation
        from computations.spectra.od_differential_spectrum import ODDifferentialSpectrumComputation
        from computations.spectra.od_walsh_spectrum import ODWalshSpectrumComputation

        try:
            g_rank = GammaRankComputation().compute_rank(apn_tt)
            apn.invariants["gamma_rank"] = g_rank
        except Exception as e:
            click.echo(f"Error computing Gamma Rank: {e}", err=True)
            apn.invariants["gamma_rank"] = None

        try:
            d_rank = DeltaRankComputation().compute_rank(apn_tt)
            apn.invariants["delta_rank"] = d_rank
        except Exception as e:
            click.echo(f"Error computing Delta Rank: {e}", err=True)
            apn.invariants["delta_rank"] = None

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

    # Univariate polynomials as input
    for poly_str in poly:
        try:
            poly_tuples = ast.literal_eval(poly_str)
            apn = parser.parse_univariate_polynomial(poly_tuples, field_n, irr_poly)
            compute_apn_properties(apn)
            compute_invariants_for_apn(apn)
            click.echo(f"Added polynomial-based APN:\n{apn}")
            apn_list.append(apn)
        except Exception as e:
            click.echo(f"Error parsing user polynomial {poly_str}: {e}", err=True)
            return

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
            click.echo(f"Added TT-based APN from {fpath}:\n{apn_tt}")
            apn_list.append(apn_tt)
        except Exception as e:
            click.echo(f"Error reading .tt file {fpath}: {e}", err=True)
            return

    save_input_apns(apn_list)