import click
from typing import List
from apn_storage_pandas import store_apn_pandas
from storage.json_storage_utils import load_input_apns_and_matches
from apn_object import APN

@click.command("store-input-apns")
def store_input_apns_cli():
    # Loads APNs from input_apns_and_matches.json and tries to store each
    # APN in the Parquet 'database' via store_apn_pandas.
    apn_dicts = load_input_apns_and_matches()
    if not apn_dicts:
        click.echo("No APNs in input_apns_and_matches.json. Add some with 'add-input'.")
        return

    for idx, apn_d in enumerate(apn_dicts, start=1):
        # Build an APN object for use with store_apn_pandas.
        in_apn = APN(
            apn_d["poly"],
            apn_d["field_n"],
            apn_d["irr_poly"]
        )
        # Merge any existing invariants.
        in_apn.invariants = apn_d.get("invariants", {})

        citation = in_apn.invariants.get("citation", f"No citation for APN {idx}")

        poly = in_apn.representation.univariate_polynomial
        field_n = in_apn.field_n
        irr_poly = in_apn.irr_poly

        click.echo(
            f"Storing APN #{idx} => poly={poly}, field_n={field_n}, irr_poly='{irr_poly}'"
        )
        store_apn_pandas(poly, field_n, irr_poly, citation)

    click.echo("Done storing APNs from input_apns_and_matches.json.")