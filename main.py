"""
# main.py

# Local imports
from user_input_parser import PolynomialParser
from apn_storage_pandas import (
    store_apn_pandas,
    load_apn_objects_for_field_pandas,
    save_apn_df_for_field,
    load_apn_df_for_field,
    poly_to_key,
    get_parquet_filename,
)
from apn_object import APN

# new main.py to be populated with CLI or other interface.
"""

import os
import json
import click
from typing import List, Set
from collections import OrderedDict
from pathlib import Path
import concurrent.futures
import multiprocessing

# Local imports from your existing modules
from user_input_parser import PolynomialParser
from apn_storage_pandas import (
    store_apn_pandas,
    load_apn_objects_for_field_pandas,
    save_apn_df_for_field,
    load_apn_df_for_field,
    poly_to_key,
    get_parquet_filename,
)
from apn_object import APN
from computations.equivalence.ccz_equivalence import CCZEquivalenceTest
# Updated reference to the renamed file/class:
from computations.equivalence.lin_eq_2x_uniform_3to1 import Uniform3to1EquivalenceTest
# Updated reference to the renamed file for checking quadratic:
from apn_is_quadratic import is_quadratic_apn
# No longer importing rank.py directly (if you still need gamma_rank, delta_rank from your older code, you can keep them)
# from rank import gamma_rank, delta_rank
# Updated references to the newly named C bindings file:
from c_spectra_bindings import (
    vbf_tt_differential_spectrum_python,
    vbf_tt_extended_walsh_spectrum_python
)
from apn_properties import compute_apn_properties

INPUT_APNS_FILE = "input_apns.json"
MATCH_LIST_FILE = "match_list.json"

def polynomial_to_str(univ_poly: List[List[int]]) -> str:
    """
    Convert a univariate polynomial (list of [coeff_exp, mon_exp])
    into a string using 'a^' for alpha-exponents and 'x^' for monomial exponents.
    Examples:
      [(0,3)] -> "x^3"
      [(1,9),(11,6),(0,3)] -> "a^1*x^9 + a^11*x^6 + x^3"
    """
    if not univ_poly:
        return "0"
    terms = []
    for (coeff_exp, mon_exp) in univ_poly:
        if coeff_exp == 0:
            alpha_part = ""
        else:
            alpha_part = f"a^{coeff_exp}"
        if mon_exp == 0:
            x_part = ""
        else:
            x_part = f"x^{mon_exp}"
        if alpha_part and x_part:
            term_str = alpha_part + "*" + x_part
        else:
            term_str = alpha_part + x_part
            if not term_str:
                term_str = "1"
        terms.append(term_str)
    return " + ".join(terms)

def reorder_invariants(invariants: dict) -> dict:
    """
    Reorder invariants so they appear in the typical DB order:
    odds, odws, gamma_rank, delta_rank, citation, k_to_1
    """
    desired_order = ["odds", "odws", "gamma_rank", "delta_rank", "citation", "k_to_1"]
    reordered = OrderedDict()
    for key in desired_order:
        if key in invariants:
            reordered[key] = invariants[key]
    for k in invariants:
        if k not in desired_order:
            reordered[k] = invariants[k]
    return dict(reordered)

def apn_summary_str(apn: APN, label="APN") -> str:
    poly_str = polynomial_to_str(apn.representation.univariate_polynomial)
    ordered_invs = reorder_invariants(apn.invariants)
    out = [
        f"{label} -> GF(2^{apn.field_n}), irreducible_poly='{apn.irr_poly}'",
        f"  Univariate polynomial representation: {poly_str}",
        f"  Properties: {apn.properties}",
        f"  Invariants: {ordered_invs}"
    ]
    return "\n".join(out)

def save_input_apns(apn_list: List[APN]) -> None:
    data = []
    for apn in apn_list:
        poly_str = polynomial_to_str(apn.representation.univariate_polynomial)
        apn_data = {
            "field_n": apn.field_n,
            "irr_poly": apn.irr_poly,
            "poly": apn.representation.univariate_polynomial,
            "poly_str": poly_str,
            "properties": apn.properties,
            "invariants": apn.invariants
        }
        data.append(apn_data)
    with open(INPUT_APNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    click.echo(f"Saved {len(apn_list)} input APNs to {INPUT_APNS_FILE}.")

def load_input_apns() -> List[APN]:
    if not os.path.isfile(INPUT_APNS_FILE):
        return []
    with open(INPUT_APNS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    apn_list = []
    parser = PolynomialParser()
    for apn_data in data:
        try:
            apn = parser.parse_univariate_polynomial(
                apn_data["poly"],
                apn_data["field_n"],
                apn_data["irr_poly"]
            )
            apn.properties = apn_data.get("properties", {})
            apn.invariants = apn_data.get("invariants", {})
            apn_list.append(apn)
        except Exception as e:
            click.echo(f"Error loading APN from file: {e}", err=True)
    return apn_list

def save_match_list(match_list: dict) -> None:
    serializable_list = {}
    for apn_idx, matches in match_list.items():
        serializable_matches = []
        for match_apn, comp_types in matches:
            poly_str = polynomial_to_str(match_apn.representation.univariate_polynomial)
            match_data = {
                "field_n": match_apn.field_n,
                "irr_poly": match_apn.irr_poly,
                "poly": match_apn.representation.univariate_polynomial,
                "poly_str": poly_str,
                "properties": match_apn.properties,
                "invariants": match_apn.invariants,
                "compare_types": list(comp_types)
            }
            serializable_matches.append(match_data)
        serializable_list[str(apn_idx)] = serializable_matches
    with open(MATCH_LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable_list, f, indent=2)
    click.echo(f"Saved match lists to {MATCH_LIST_FILE}.")

def load_match_list() -> dict:
    if not os.path.isfile(MATCH_LIST_FILE):
        return {}
    with open(MATCH_LIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    match_list = {}
    parser = PolynomialParser()
    for apn_idx_str, matches in data.items():
        apn_idx = int(apn_idx_str)
        match_entries = []
        for match_data in matches:
            try:
                apn = parser.parse_univariate_polynomial(
                    match_data["poly"],
                    match_data["field_n"],
                    match_data["irr_poly"]
                )
                apn.properties = match_data.get("properties", {})
                apn.invariants = match_data.get("invariants", {})
                compare_types_list = match_data.get("compare_types", [])
                compare_types_set = set(compare_types_list)
                match_entries.append((apn, compare_types_set))
            except Exception as e:
                click.echo(f"Error loading match APN: {e}", err=True)
        match_list[apn_idx] = match_entries
    return match_list

def ccz_check_multiproc(args) -> bool:
    (in_tt, matched_tt) = args
    ccz_test = CCZEquivalenceTest()
    from apn_object import APN
    from representations.truth_table_representation import TruthTableRepresentation
    # We wrap them into ephemeral APN objects:
    apnF = APN.from_representation(TruthTableRepresentation(in_tt), 1, "0")
    apnG = APN.from_representation(TruthTableRepresentation(matched_tt), 1, "0")
    try:
        return ccz_test.are_equivalent(apnF, apnG)
    except Exception:
        return False

@click.group()
def cli():
    """
    A CLI for handling APNs, storing them in a database, comparing spectra/ranks,
    checking CCZ-equivalence, and more.
    """
    pass

##############################################################################
# CLI COMMAND: add-input
##############################################################################

@cli.command("add-input")
@click.option("--poly", "-p", multiple=True)
@click.option("--poly-file", type=click.Path(exists=True), multiple=True)
@click.option("--field-n", default=None, type=int)
@click.option("--irr-poly", default="", type=str)
def add_input(poly, poly_file, field_n, irr_poly):
    import ast
    from representations.truth_table_representation import TruthTableRepresentation

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

        # We'll import the new modular classes for rank and spectra
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
                apn.invariants["odds"] = "Non-quadratic"
            try:
                odws_res = ODWalshSpectrumComputation().compute_spectrum(apn_tt)
                apn.invariants["odws"] = {int(k): int(v) for k, v in odws_res.items()}
            except Exception as e:
                click.echo(f"Error computing OD Extended Walsh Spectrum: {e}", err=True)
                apn.invariants["odws"] = "Non-quadratic"
        else:
            apn.invariants["odds"] = "Non-quadratic"
            apn.invariants["odws"] = "Non-quadratic"

    # Handle polynomials directly
    for poly_str in poly:
        try:
            poly_tuples = ast.literal_eval(poly_str)
            apn = parser.parse_univariate_polynomial(poly_tuples, field_n, irr_poly)
            compute_apn_properties(apn)
            compute_invariants_for_apn(apn)
            click.echo(f"Added polynomial-based APN:\n{apn_summary_str(apn, label='INPUT_APN')}")
            apn_list.append(apn)
        except Exception as e:
            click.echo(f"Error parsing user polynomial {poly_str}: {e}", err=True)
            return

    # Handle polynomial from .tt files
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
            click.echo(f"Added TT-based APN from {fpath}:\n{apn_summary_str(apn_tt, label='INPUT_APN')}")
            apn_list.append(apn_tt)
        except Exception as e:
            click.echo(f"Error reading .tt file {fpath}: {e}", err=True)
            return

    save_input_apns(apn_list)

##############################################################################
# CLI COMMAND: compare
##############################################################################

@cli.command("compare")
@click.option("--compare-type", type=click.Choice(["odds", "odws", "delta", "gamma", "all"]), default="all")
@click.option("--field-n", required=True, type=int)
@click.option("--debug", is_flag=True)
def compare_apns(compare_type, field_n, debug):
    apn_list = load_input_apns()
    match_list = load_match_list()
    if not apn_list:
        click.echo("No APNs in the input list. Please run 'add-input' first.")
        return

    db_apns = load_apn_objects_for_field_pandas(field_n)
    if not db_apns:
        click.echo(f"No APNs found in the database for GF(2^{field_n}).")
        return

    if debug:
        click.echo(f"\nDebug Mode: Listing {len(db_apns)} DB APNs for GF(2^{field_n}):")
        for idx, db_apn in enumerate(db_apns):
            click.echo(f"\nDB_APN {idx}:\n{apn_summary_str(db_apn, label='DB_APN')}")
        click.echo("\nEnd of DB APNs.\n")

    for input_idx, in_apn in enumerate(apn_list):
        if input_idx not in match_list:
            match_list[input_idx] = []

        existing_matches_map = {}
        for (m_apn, comp_types) in match_list[input_idx]:
            m_key = (
                m_apn.field_n,
                m_apn.irr_poly,
                tuple(tuple(term) for term in m_apn.representation.univariate_polynomial)
            )
            existing_matches_map[m_key] = (m_apn, comp_types)

        in_odds = in_apn.invariants.get("odds", "Non-quadratic")
        in_odws = in_apn.invariants.get("odws", "Non-quadratic")
        in_gamma = in_apn.invariants.get("gamma_rank", None)
        in_delta = in_apn.invariants.get("delta_rank", None)
        in_is_quad = in_apn.properties.get("is_quadratic", False)

        if not in_is_quad and compare_type in ["odds", "odws", "all"]:
            click.echo(f"For INPUT_APN {input_idx}, it is non-quadratic. Only gamma/delta can be compared.")
            if compare_type == "all":
                relevant_types = ["gamma", "delta"]
            elif compare_type in ["odds", "odws"]:
                relevant_types = []
            else:
                relevant_types = [compare_type]
        else:
            if compare_type == "all":
                relevant_types = ["odds", "odws", "gamma", "delta"]
            else:
                relevant_types = [compare_type]

        for db_index, db_apn in enumerate(db_apns):
            is_match = True
            db_odds = db_apn.invariants.get("odds", "Non-quadratic")
            db_odws = db_apn.invariants.get("odws", "Non-quadratic")
            db_gamma = db_apn.invariants.get("gamma_rank", None)
            db_delta = db_apn.invariants.get("delta_rank", None)

            for comp in relevant_types:
                if comp == "odds":
                    if in_odds != db_odds:
                        is_match = False
                        break
                elif comp == "odws":
                    if in_odws != db_odws:
                        is_match = False
                        break
                elif comp == "gamma":
                    if in_gamma != db_gamma:
                        is_match = False
                        break
                elif comp == "delta":
                    if in_delta != db_delta:
                        is_match = False
                        break

            if is_match:
                db_key = (
                    db_apn.field_n,
                    db_apn.irr_poly,
                    tuple(tuple(term) for term in db_apn.representation.univariate_polynomial)
                )
                if db_key in existing_matches_map:
                    (stored_apn, stored_comp_types) = existing_matches_map[db_key]
                    stored_comp_types.add(compare_type)
                else:
                    new_set = set([compare_type])
                    existing_matches_map[db_key] = (db_apn, new_set)

        new_matches_list = list(existing_matches_map.values())
        match_list[input_idx] = new_matches_list

        click.echo(f"For INPUT_APN {input_idx}, after comparing by '{compare_type}', "
                   f"found {len(match_list[input_idx])} matching APNs so far.")

    save_match_list(match_list)

##############################################################################
# CLI COMMAND: ccz
##############################################################################

@cli.command("ccz")
@click.option("--input-apn-index", default=0, type=int)
def ccz_equivalence_check(input_apn_index):
    apn_list = load_input_apns()
    match_list = load_match_list()

    if input_apn_index < 0 or input_apn_index >= len(apn_list):
        click.echo("Invalid input APN index.")
        return
    if input_apn_index not in match_list or not match_list[input_apn_index]:
        click.echo("No matches in match-list. Run 'compare' first.")
        return

    in_apn = apn_list[input_apn_index]
    matches = match_list[input_apn_index]
    if not matches:
        click.echo("No matches to check for CCZ-equivalence.")
        return

    in_tt = in_apn.get_truth_table().representation.truth_table
    tasks = []
    for (m_apn, comp_types) in matches:
        matched_tt = m_apn.get_truth_table().representation.truth_table
        tasks.append((in_tt, matched_tt))

    num_cpus = multiprocessing.cpu_count()
    max_workers = num_cpus * 2
    updated_matches = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(ccz_check_multiproc, tasks))

    removed_count = 0
    for i, (m_apn, comp_types) in enumerate(matches):
        eq = results[i]
        if eq:
            removed_count += 1
            click.echo(
                f"  * CCZ-Equivalent with:\n{apn_summary_str(m_apn, label='DB_APN')} "
                f"-> removing from match list."
            )
        else:
            click.echo(
                f"  * NOT CCZ-Equivalent with:\n{apn_summary_str(m_apn, label='DB_APN')} "
                f"-> keeping in match list."
            )
            updated_matches.append((m_apn, comp_types))

    match_list[input_apn_index] = updated_matches
    save_match_list(match_list)
    click.echo(
        f"Removed {removed_count} APNs due to CCZ equivalence. "
        f"After CCZ equivalence check, {len(updated_matches)} APNs remain in the match list for INPUT_APN {input_apn_index}."
    )

##############################################################################
# CLI COMMAND: 3to1
##############################################################################

@cli.command("3to1")
@click.option("--input-apn-index", default=0, type=int)
def three_to1_equivalence_check(input_apn_index):
    """
    Runs the 3-to-1 linear equivalence test on the APNs in the match list 
    for the given input APN. This test is only applicable if the input APN has 
    property 'k_to_1' == '3-to-1'. Matches that are 3-to-1 are checked, 
    and if equivalent, removed from the match list.
    """
    apn_list = load_input_apns()
    match_list = load_match_list()

    if input_apn_index < 0 or input_apn_index >= len(apn_list):
        click.echo("Invalid input APN index.")
        return
    if input_apn_index not in match_list or not match_list[input_apn_index]:
        click.echo("No matches in the match list. Run 'compare' first.")
        return

    in_apn = apn_list[input_apn_index]
    if in_apn.properties.get("k_to_1") != "3-to-1":
        click.echo("Input APN does not have the required property: k_to_1 must be '3-to-1'.")
        return

    updated_matches = []
    removed_count = 0

    matches = match_list[input_apn_index]
    # Updated reference to the renamed class:
    uniform3to1_test = Uniform3to1EquivalenceTest()

    for (m_apn, comp_types) in matches:
        if m_apn.properties.get("k_to_1") == "3-to-1":
            eq = False
            try:
                eq = uniform3to1_test.are_equivalent(in_apn, m_apn)
            except Exception as e:
                click.echo(f"Error during 3-to-1 equivalence test: {e}", err=True)

            if eq:
                removed_count += 1
                click.echo(
                    f"3-to-1 equivalent: Removing match:\n{apn_summary_str(m_apn, label='DB_APN')}"
                )
            else:
                updated_matches.append((m_apn, comp_types))
        else:
            updated_matches.append((m_apn, comp_types))

    match_list[input_apn_index] = updated_matches
    save_match_list(match_list)
    click.echo(
        f"3-to-1 equivalence test removed {removed_count} APNs from match list "
        f"for INPUT_APN {input_apn_index}."
    )

##############################################################################
# CLI COMMAND: print-matches
##############################################################################

@cli.command("print-matches")
@click.option("--input-apn-index", default=None, type=int)
def print_matches(input_apn_index):
    apn_list = load_input_apns()
    match_list = load_match_list()

    if not match_list:
        click.echo("No match-lists found. Please run 'compare' first.")
        return

    if input_apn_index is None:
        for idx, matches in match_list.items():
            in_apn = apn_list[idx]
            click.echo(f"\nINPUT_APN {idx} =>\n{apn_summary_str(in_apn, label=f'INPUT_APN {idx}')}") 
            click.echo(f"Matches found: {len(matches)}")
            for match_apn, comp_types in matches:
                click.echo(f"  - Matched on {sorted(comp_types)} with:\n{apn_summary_str(match_apn, label='DB_APN')}")
    else:
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo("Invalid input APN index.")
            return
        if input_apn_index not in match_list:
            click.echo(f"No matches exist for INPUT_APN {input_apn_index}.")
            return
        matches = match_list[input_apn_index]
        in_apn = apn_list[input_apn_index]
        click.echo(f"\nINPUT_APN {input_apn_index} =>\n{apn_summary_str(in_apn, label=f'INPUT_APN {input_apn_index}')}") 
        click.echo(f"Matches found: {len(matches)}")
        for match_apn, comp_types in matches:
            click.echo(f"  - Matched on {sorted(comp_types)} with:\n{apn_summary_str(match_apn, label='DB_APN')}")

##############################################################################
# CLI COMMAND: save-matches
##############################################################################

@cli.command("save-matches")
@click.option("--output-file", default="matches_output.json", type=str)
def save_matches(output_file):
    apn_list = load_input_apns()
    match_list = load_match_list()

    if not match_list:
        click.echo("No matches to save. Please run 'compare' first.")
        return

    output_data = {}
    for idx, matches in match_list.items():
        in_apn = apn_list[idx]
        in_apn_poly_str = polynomial_to_str(in_apn.representation.univariate_polynomial)
        in_apn_summary = {
            "field_n": in_apn.field_n,
            "irr_poly": in_apn.irr_poly,
            "poly": in_apn.representation.univariate_polynomial,
            "poly_str": in_apn_poly_str,
            "properties": in_apn.properties,
            "invariants": in_apn.invariants
        }
        matches_list = []
        for match_apn, comp_types in matches:
            match_apn_poly_str = polynomial_to_str(match_apn.representation.univariate_polynomial)
            matches_list.append({
                "compare_types": list(comp_types),
                "field_n": match_apn.field_n,
                "irr_poly": match_apn.irr_poly,
                "poly": match_apn.representation.univariate_polynomial,
                "poly_str": match_apn_poly_str,
                "properties": match_apn.properties,
                "invariants": match_apn.invariants,
            })

        output_data[f"input_apn_{idx}"] = {
            "input_apn": in_apn_summary,
            "matches": matches_list
        }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    click.echo(f"Matches saved to {output_file}")

##############################################################################
# CLI COMMAND: reset-storage
##############################################################################

@cli.command("reset-storage")
@click.option("--yes", "-y", is_flag=True)
def reset_storage(yes):
    if not yes:
        click.confirm(
            "Are you sure you want to erase all stored APNs and match lists? This action cannot be undone.",
            abort=True
        )
    files_to_delete = [INPUT_APNS_FILE, MATCH_LIST_FILE]
    deleted_files = []
    for file in files_to_delete:
        if os.path.isfile(file):
            try:
                os.remove(file)
                deleted_files.append(file)
            except Exception as e:
                click.echo(f"Error deleting {file}: {e}", err=True)

    if deleted_files:
        click.echo(f"Deleted files: {', '.join(deleted_files)}")
    else:
        click.echo("No storage files found to delete.")

##############################################################################
# CLI COMMAND: compute-match-properties
##############################################################################

@cli.command("compute-match-properties")
@click.option("--input-apn-index", default=None, type=int)
def compute_match_properties(input_apn_index):
    """
    For each APN in the match list (and for its matched APNs), compute polynomial
    properties (degree, DU, is_quadratic, is_monomial, k_to_1, etc.). This does 
    not directly store anything back to the database, but updates the APN objects 
    in memory so you can inspect them with 'print-matches'.
    
    We also call save_input_apns(...) and save_match_list(...), so these updated 
    properties remain on disk.
    """
    apn_list = load_input_apns()
    match_list = load_match_list()

    if not apn_list:
        click.echo("No APNs in input list. Please run 'add-input' first.")
        return

    if not match_list:
        click.echo("No matches available. Please run 'compare' first.")
        return

    def compute_for_apn(apn: APN):
        compute_apn_properties(apn)
        click.echo(f"Computed properties for:\n{apn_summary_str(apn)}")

    if input_apn_index is None:
        for idx, matches in match_list.items():
            input_apn = apn_list[idx]
            compute_for_apn(input_apn)
            for (m_apn, _) in matches:
                compute_for_apn(m_apn)
        save_input_apns(apn_list)
        save_match_list(match_list)
        click.echo("Finished computing properties for all matched APNs (and saved updates).")
    else:
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo("Invalid input APN index.")
            return
        if input_apn_index not in match_list or not match_list[input_apn_index]:
            click.echo("No matches in match-list for this APN index. Run 'compare' first.")
            return

        input_apn = apn_list[input_apn_index]
        matches = match_list[input_apn_index]

        compute_for_apn(input_apn)
        for (m_apn, _) in matches:
            compute_for_apn(m_apn)

        save_input_apns(apn_list)
        save_match_list(match_list)
        click.echo(
            f"Finished computing properties for INPUT_APN {input_apn_index} "
            f"and its matched APNs (and saved updates)."
        )

if __name__ == "__main__":
    cli()