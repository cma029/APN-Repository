import click
from storage_pandas import load_objects_for_dimension_pandas
from cli_commands.cli_utils import build_vbf_from_dict, format_generic_vbf, polynomial_to_str

@click.command("read-db")
@click.option("--dim", "dimension_n", required=True, type=int,
              help="The dimension n for GF(2^n).")
@click.option("--range", "vbf_range", nargs=2, type=int, default=None,
              help="Optional range <start> <end> of VBF indexes to print.")
@click.option("--save-to-file", "save_to_file", is_flag=True,
              help="Saves the selected univariate polynomials to {dim_n}bit_db_unipoly.txt.")
def read_db(dimension_n, vbf_range, save_to_file):
    # Loads, prints or saves (file name {dim_n}bit_db_unipoly.txt) VBFs from the database.
    click.echo(f"Loading VBFs for dimension n = {dimension_n}...")

    vbf_list = load_objects_for_dimension_pandas(dimension_n)
    if not vbf_list:
        click.echo(f"No VBFs found for dimension n = {dimension_n}.")
        return

    click.echo(f"Total VBFs loaded for dimension n = {dimension_n}: {len(vbf_list)}\n")

    # Option: --range <start> <end> for a custom range.
    if vbf_range is not None:
        start_idx, end_idx = vbf_range
        subset = vbf_list[start_idx - 1 : end_idx]
        if not subset:
            click.echo(f"No VBFs in the requested range {start_idx}-{end_idx}.")
            return
        start_offset = start_idx
    else:
        # By default: prints the first 5.
        subset = vbf_list[:5]
        start_offset = 1

    click.echo(f"VBF GF(2^{dimension_n}) Details:")
    click.echo("-" * 100)
    for idx, vbf_object in enumerate(subset, start=start_offset):
        click.echo(format_generic_vbf(vbf_object, f"VBF {idx}"))
        click.echo("-" * 100)

    if save_to_file:
        if vbf_range is not None:
            vbfs_to_export = subset
        else:
            # If no range, then save the entire list.
            vbfs_to_export = vbf_list

        out_filename = f"{dimension_n}bit_db_unipoly.txt"
        click.echo(f"\nSaving univariate polynomials to '{out_filename}'...")

        with open(out_filename, "w", encoding="utf-8") as file:
            # First line is the field n dimension.
            file.write(f"{dimension_n}\n")

            for vbf_object in vbfs_to_export:
                if hasattr(vbf_object.representation, "univariate_polynomial"):
                    poly_str = polynomial_to_str(vbf_object.representation.univariate_polynomial)
                    file.write(poly_str + "\n")
                else:
                    # In case a VBF has no univariate polynomial we fallback.
                    file.write("0\n")

        click.echo(f"Saved {len(vbfs_to_export)} polynomial(s) to '{out_filename}'.")