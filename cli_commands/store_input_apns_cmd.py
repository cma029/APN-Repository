# store_input_apns_cmd.py

import click
from apn_storage_pandas import store_apn_pandas, load_input_apns
from apn_object import APN

@click.command("store-input-apns")
def store_input_apns_cli():
    # Loads APNs from input_apns.json and tries to store each in the
    # Parquet database. If an APN already exists, it is skipped.
    apn_list = load_input_apns()
    if not apn_list:
        click.echo("No APNs in input_apns.json. Add some with 'add-input'.")
        return

    for idx, apn in enumerate(apn_list, start=1):
        poly = apn.representation.univariate_polynomial
        field_n = apn.field_n
        irr_poly = apn.irr_poly
        citation = apn.invariants.get("citation", f"No citation for APN {idx}")
        click.echo(f"Storing APN #{idx} => poly={poly}, field_n={field_n}, irr_poly='{irr_poly}'")
        store_apn_pandas(poly, field_n, irr_poly, citation)

    click.echo("Done storing APNs from input_apns.json.")