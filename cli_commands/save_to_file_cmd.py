import click
import json
from typing import List, Dict, Any
from cli_commands.cli_utils import polynomial_to_str, build_apn_from_dict
from storage.json_storage_utils import load_input_apns_and_matches

@click.command("save")
@click.option("--file-name", default=None, type=str,
              help="If exporting only one type, you can override the default filename.")
@click.option("--matches", is_flag=True,
              help="Export the input and matches in JSON format.")
@click.option("--poly", is_flag=True,
              help="Export the APN(s) polynomials in a text file (one per line).")
@click.option("--tt", is_flag=True,
              help="Export the APN(s) in a truth table format (one per line).")
def save_to_file_cli(file_name, matches, poly, tt):
    """
    Various exports of data from storage/input_apns_and_matches.json to file(s).

    Usage examples:
        python main.py save --poly --file-name my_8bit_polys.txt
        => exports polynomials to a single text file.
    """
    input_apn_list = load_input_apns_and_matches()
    if not input_apn_list:
        click.echo("No input APNs found. Please run 'add-input' first.")
        return

    # If no options were given, print error.
    if not (matches or poly or tt):
        click.echo("Error: Must specify at least one of --matches, --poly, or --tt.")
        return

    # If multiple flags are selected, we produce multiple files with default names.
    selected_modes = []
    if matches:
        selected_modes.append("matches")
    if poly:
        selected_modes.append("poly")
    if tt:
        selected_modes.append("tt")

    # If user selected exactly one type, we can use the --file-name option.
    multiple_selections = (len(selected_modes) > 1)

    # File name for each selected mode.
    if "matches" in selected_modes:
        # Choose filename
        if (not multiple_selections) and (file_name is not None):
            matches_filename = file_name
        else:
            matches_filename = "matches_output.json"

        _export_matches_json(input_apn_list, matches_filename)
        click.echo(f"Matches saved to {matches_filename}")

    if "poly" in selected_modes:
        # Choose filename
        if (not multiple_selections) and (file_name is not None):
            poly_filename = file_name
        else:
            poly_filename = "poly_output.txt"

        _export_poly(input_apn_list, poly_filename)
        click.echo(f"Polynomials saved to {poly_filename}")

    if "tt" in selected_modes:
        # Choose filename
        if (not multiple_selections) and (file_name is not None):
            tt_filename = file_name
        else:
            tt_filename = "tt_output.txt"

        _export_tt(input_apn_list, tt_filename)
        click.echo(f"Truth tables saved to {tt_filename}")


def _export_matches_json(input_apn_list: List[Dict[str, Any]], output_file: str):
    # Export the matches in JSON format.
    output_json_data = {}

    for input_index, apn_dictionary in enumerate(input_apn_list):
        apn_object = build_apn_from_dict(apn_dictionary)
        input_poly_str = polynomial_to_str(apn_object.representation.univariate_polynomial)

        input_apn_summary = {
            "field_n": apn_object.field_n,
            "irr_poly": apn_object.irr_poly,
            "poly": apn_object.representation.univariate_polynomial,
            "poly_str": input_poly_str,
            "invariants": apn_object.invariants
        }

        # Gather the matches (if any) for this input APN.
        output_matches_list = []
        matches_list = apn_dictionary.get("matches", [])
        for match_dict in matches_list:
            match_apn_obj = build_apn_from_dict(match_dict)
            match_poly_str = polynomial_to_str(match_apn_obj.representation.univariate_polynomial)
            compare_types_value = match_dict.get("compare_types", [])
            if isinstance(compare_types_value, set):
                compare_types_value = list(compare_types_value)

            output_matches_list.append({
                "compare_types": compare_types_value,
                "field_n": match_apn_obj.field_n,
                "irr_poly": match_apn_obj.irr_poly,
                "poly": match_apn_obj.representation.univariate_polynomial,
                "poly_str": match_poly_str,
                "invariants": match_apn_obj.invariants
            })

        output_json_data[f"input_apn_{input_index}"] = {
            "input_apn": input_apn_summary,
            "matches": output_matches_list
        }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_json_data, f, indent=2)


def _export_poly(input_apn_list: List[Dict[str, Any]], output_file: str):
    # Exports APN(s) in univariate polynomial representation to a text file.
    if not input_apn_list:
        click.echo(f"No APNs to export for --poly to {output_file}")
        return

    # Use the dimension of the first APN.
    first_apn_object = build_apn_from_dict(input_apn_list[0])
    base_dim = first_apn_object.field_n

    # All APN(s) must have the same field_n dimension.
    for idx, apn_dict in enumerate(input_apn_list):
        apn_object = build_apn_from_dict(apn_dict)
        if apn_object.field_n != base_dim:
            click.echo(f"Error: APN #{idx} has field_n={apn_object.field_n}, expected {base_dim}.")
            click.echo("Aborting --poly export due to mixed dimensions.")
            return

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"{base_dim}\n")  # The first line is field n dimension.
        for apn_dict in input_apn_list:
            apn_object = build_apn_from_dict(apn_dict)
            poly_str = polynomial_to_str(apn_object.representation.univariate_polynomial)
            f.write(f"{poly_str}\n")


def _export_tt(input_apn_list: List[Dict[str, Any]], output_file: str):
    # Exports APN(s) in truth table representation to a text file.
    if not input_apn_list:
        click.echo(f"No APNs to export for --tt to {output_file}")
        return

    # Use the dimension of the first APN.
    first_apn_obj = build_apn_from_dict(input_apn_list[0])
    base_dim = first_apn_obj.field_n

    # All APN(s) must have the same field_n dimension.
    for idx, apn_dict in enumerate(input_apn_list):
        apn_object = build_apn_from_dict(apn_dict)
        if apn_object.field_n != base_dim:
            click.echo(f"Error: APN #{idx} has field_n={apn_object.field_n}, expected {base_dim}.")
            click.echo("Aborting --tt export due to mixed dimensions.")
            return

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"{base_dim}\n")  # The first line is field n dimension.
        for apn_dict in input_apn_list:
            apn_object = build_apn_from_dict(apn_dict)
            rep = apn_object.get_truth_table()  # or apn_obj._get_truth_table_list()
            tt_values = rep.truth_table

            # Write each APN's truth table on a separate line.
            f.write(" ".join(str(x) for x in tt_values))
            f.write("\n")