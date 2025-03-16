import click
from apn_storage_pandas import load_apn_objects_for_field_pandas
from cli_commands.cli_utils import format_generic_apn, polynomial_to_str

@click.command("read-db")
@click.option("--field-n", required=True, type=int,
              help="The field n dimension for GF(2^n).")
@click.option("--range", "apn_range", nargs=2, type=int, default=None,
              help="Optional range <start> <end> of APN indexes to print.")
@click.option("--save-to-file", is_flag=True,
              help="Saves the selected univariate polynomials to {field_n}bit_db_unipoly.txt.")
def read_db_apns(field_n, apn_range, save_to_file):
    # Loads, prints or saves (file name {field_n}bit_db_unipoly.txt) APNs from the database.
    click.echo(f"Loading APNs for field_n={field_n}...")
    apn_list = load_apn_objects_for_field_pandas(field_n)
    if not apn_list:
        click.echo(f"No APNs found for field_n={field_n}.")
        return

    click.echo(f"Total APNs loaded for field_n={field_n}: {len(apn_list)}\n")

    # Option: --range <start> <end> for a custom range.
    if apn_range is not None:
        start_idx, end_idx = apn_range
        subset = apn_list[start_idx - 1 : end_idx]
        if not subset:
            click.echo(f"No APNs in the requested range {start_idx}-{end_idx}.")
            return
        start_offset = start_idx
    else:
        # By default: prints the first 10.
        subset = apn_list[:10]
        start_offset = 1

    click.echo(f"APN GF(2^{field_n}) Details:")
    click.echo("-" * 100)
    for idx, apn in enumerate(subset, start=start_offset):
        click.echo(format_generic_apn(apn, f"APN {idx}"))
        click.echo("-" * 100)

    if save_to_file:
        if apn_range is not None:
            apns_to_export = subset
        else:
            # If no range, then save the entire list.
            apns_to_export = apn_list

        out_filename = f"{field_n}bit_db_unipoly.txt"
        click.echo(f"\nSaving univariate polynomials to '{out_filename}'...")

        with open(out_filename, "w", encoding="utf-8") as f:
            # First line is the field n dimension.
            f.write(f"{field_n}\n")

            for apn_object in apns_to_export:
                if hasattr(apn_object.representation, "univariate_polynomial"):
                    poly_str = polynomial_to_str(apn_object.representation.univariate_polynomial)
                    f.write(poly_str + "\n")
                else:
                    # In case an APN has no univariate polynomial we fallback.
                    f.write("0\n")

        click.echo(f"Saved {len(apns_to_export)} polynomial(s) to '{out_filename}'.")