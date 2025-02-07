# uni3to1_cmd.py

import click
from apn_storage_pandas import (
    load_input_apns, save_input_apns,
    load_match_list, save_match_list,
    EQUIV_LIST_FILE, load_equivalence_list, save_equivalence_list
)
from apn_object import APN
from computations.equivalence.lin_eq_2x_uniform_3to1 import Uniform3to1EquivalenceTest
from representations.truth_table_representation import TruthTableRepresentation
import concurrent.futures

@click.command("uni3to1")
@click.option("--input-apn-index", default=0, type=int)
def uni3to1_equivalence_cli(input_apn_index):
    # Runs 3-to-1 (uniformly distributed) linear equivalence test.
    apn_list = load_input_apns()
    match_list_data = load_match_list()

    matches = match_list_data[input_apn_index]
    removed_count = 0
    found_equiv_apn = None

    for i, (m_apn, comp_types) in enumerate(matches):
        if m_apn.properties.get("k_to_1") == "3-to-1":
            eq = _uni3to1_single(in_apn, m_apn)
            if eq:
                _store_equivalence_record(in_apn, m_apn, eq_type="uni3to1")
                _remove_apn_from_input_and_matches(in_apn, apn_list, match_list_data)
                match_list_data.pop(input_apn_index, None)

                removed_count += 1
                found_equiv_apn = m_apn
                break

    save_input_apns(apn_list)
    save_match_list(match_list_data)

    # If found equivalent, remove APN from input_apns and store in equivalence_list.
    if found_equiv_apn:
        click.echo(
            f"APN #{input_apn_index} was 3-to-1 equivalent with another APN.\n"
            f"Removed from input_apns, recorded in equivalence_list."
        )
    else:
        click.echo("No 3-to-1 equivalence found for that APN index.")

def _uni3to1_single(in_apn, m_apn):
    eq_test = Uniform3to1EquivalenceTest()
    return eq_test.are_equivalent(in_apn, m_apn)

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
        "matched_apn": apn_to_dict(m_apn)
    }
    eq_list.append(record)
    save_equivalence_list(eq_list)