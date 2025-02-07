import click
import concurrent.futures
from apn_storage_pandas import load_match_list, save_match_list
from storage.input_json_storage import load_input_apns, save_input_apns
from computations.equivalence.ccz_equivalence import CCZEquivalenceTest
from apn_object import APN
from representations.truth_table_representation import TruthTableRepresentation
from typing import Optional
from user_input_parser import PolynomialParser
import os
import json

from apn_storage_pandas import (
    EQUIV_LIST_FILE, load_equivalence_list, save_equivalence_list
)

@click.command("ccz")
@click.option("--input-apn-index", default=0, type=int)
def ccz_equivalence_cli(input_apn_index):
    # Runs CCZ equivalence check on the matches of a given input APN.
    apn_list = load_input_apns()
    match_list_data = load_match_list()

    if input_apn_index < 0 or input_apn_index >= len(apn_list):
        click.echo("Invalid input APN index.")
        return

    if input_apn_index not in match_list_data or not match_list_data[input_apn_index]:
        click.echo("No matches in match-list. Run 'compare' first.")
        return

    in_apn = apn_list[input_apn_index]
    matches = match_list_data[input_apn_index]
    if not matches:
        click.echo("No matches to check for CCZ-equivalence.")
        return

    in_tt = in_apn.get_truth_table().representation.truth_table

    removed_count = 0
    found_equiv_apn = None

    for i, (m_apn, comp_types) in enumerate(matches):
        matched_tt = m_apn.get_truth_table().representation.truth_table
        eq = False
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_ccz_single, in_tt, matched_tt)
            eq = future.result()

        if eq:
            # If found equivalent, the APN is stored in equivalence_list.json
            # and removed from input_apns. The match is also removed from match_list.
            _store_equivalence_record(in_apn, m_apn, eq_type="ccz")
            _remove_apn_from_input_and_matches(in_apn, apn_list, match_list_data)
            match_list_data.pop(input_apn_index, None)

            removed_count += 1
            found_equiv_apn = m_apn
            break

    save_input_apns(apn_list)
    save_match_list(match_list_data)

    if found_equiv_apn:
        click.echo(
            f"APN #{input_apn_index} was CCZ-equivalent with a matched APN.\n"
            f"Removed from input_apns and recorded in equivalence_list."
        )
    else:
        click.echo("No CCZ equivalence found for that APN index.")

def _ccz_single(in_tt, matched_tt):
    ccz_test = CCZEquivalenceTest()
    apnF = APN.from_representation(TruthTableRepresentation(in_tt), 1, "0")
    apnG = APN.from_representation(TruthTableRepresentation(matched_tt), 1, "0")
    return ccz_test.are_equivalent(apnF, apnG)

def _remove_apn_from_input_and_matches(apn, apn_list, match_list_data):
    if apn in apn_list:
        apn_list.remove(apn)

    for idx, matches in match_list_data.items():
        new_matches = []
        for (m_apn, comp_types) in matches:
            if m_apn == apn:
                pass
            else:
                new_matches.append((m_apn, comp_types))
        match_list_data[idx] = new_matches

def _store_equivalence_record(input_apn, matched_apn, eq_type: str):
    eq_list = load_equivalence_list()

    def apn_to_dict(a):
        return {
            "poly": a.representation.univariate_polynomial,
            "field_n": a.field_n,
            "irr_poly": a.irr_poly,
            "properties": a.properties,
            "invariants": a.invariants
        }

    record = {
        "eq_type": eq_type,
        "input_apn": apn_to_dict(input_apn),
        "matched_apn": apn_to_dict(matched_apn)
    }
    eq_list.append(record)
    save_equivalence_list(eq_list)