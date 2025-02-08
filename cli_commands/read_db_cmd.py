import click
from apn_storage_pandas import load_apn_objects_for_field_pandas
from cli_commands.cli_utils import format_generic_apn
from typing import Optional
from apn_object import APN

@click.command("read-db-apns")
@click.option("--field-n", required=True, type=int,
              help="The dimension n for GF(2^n).")
@click.option("--range", "apn_range", nargs=2, type=int, default=None,
              help="Optional range (start end) of APN indexes to print.")
def read_db_apns(field_n, apn_range):
    # Loads and prints APNs from the database.
    click.echo(f"Loading APNs for field_n={field_n}...")
    apn_list = load_apn_objects_for_field_pandas(field_n)
    if not apn_list:
        click.echo(f"No APNs found for field_n={field_n}.")
        return

    click.echo(f"Total APNs loaded for field_n={field_n}: {len(apn_list)}\n")

    # Option: --range start end for a custom range.
    if apn_range is not None:
        start_idx, end_idx = apn_range
        subset = apn_list[start_idx - 1 : end_idx]
        if not subset:
            click.echo(f"No APNs in the requested range {start_idx}-{end_idx}.")
            return
        start_offset = start_idx
    else:
        # By default: prints the first 10
        subset = apn_list[:10]
        start_offset = 1

    click.echo(f"APN GF(2^{field_n}) Details:")
    click.echo("-" * 100)
    for i, apn in enumerate(subset, start=start_offset):
        click.echo(format_generic_apn(apn, f"APN {i}"))
        click.echo("-" * 100)