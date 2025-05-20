import click
import json
from typing import List, Dict, Any
from cli_commands.cli_utils import polynomial_to_str, build_vbf_from_dict
from storage.json_storage_utils import load_input_vbfs_and_matches

@click.command("save")
@click.option("--file-name", default=None, type=str,
              help="If exporting only one type, you can override the default filename.")
@click.option("--matches", is_flag=True,
              help="Export the input and matches in JSON format.")
@click.option("--poly", is_flag=True,
              help="Export the VBF(s) polynomials in a text file (one per line).")
@click.option("--tt", is_flag=True,
              help="Export the VBF(s) in a truth table format (one per line).")
def save_to_file_cli(file_name, matches, poly, tt):
    """
    Various exports of data from storage/input_vbfs_and_matches.json to file(s).

    Usage examples:
        python main.py save --poly --file-name my_8bit_polys.txt
        => exports polynomials to a single text file.
    """
    input_vbf_list = load_input_vbfs_and_matches()
    if not input_vbf_list:
        click.echo("No input VBFs found. Please run 'add-input' first.")
        return

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

    if "matches" in selected_modes:
        if (not multiple_selections) and (file_name is not None):
            matches_filename = file_name
        else:
            matches_filename = "matches_output.json"

        _export_matches_json(input_vbf_list, matches_filename)
        click.echo(f"Matches saved to {matches_filename}")

    if "poly" in selected_modes:
        if (not multiple_selections) and (file_name is not None):
            poly_filename = file_name
        else:
            poly_filename = "poly_output.txt"

        _export_poly(input_vbf_list, poly_filename)
        click.echo(f"Polynomials saved to {poly_filename}")

    if "tt" in selected_modes:
        if (not multiple_selections) and (file_name is not None):
            tt_filename = file_name
        else:
            tt_filename = "tt_output.txt"

        _export_tt(input_vbf_list, tt_filename)
        click.echo(f"Truth tables saved to {tt_filename}")


def _export_matches_json(input_vbf_list: List[Dict[str, Any]], output_file: str):
    # Export the matches in JSON format.
    output_json_data = {}

    for input_index, vbf_dictionary in enumerate(input_vbf_list):
        vbf_object = build_vbf_from_dict(vbf_dictionary)
        input_poly_str = polynomial_to_str(vbf_object.representation.univariate_polynomial)

        input_vbf_summary = {
            "field_n": vbf_object.field_n,
            "irr_poly": vbf_object.irr_poly,
            "poly": vbf_object.representation.univariate_polynomial,
            "poly_str": input_poly_str,
            "invariants": vbf_object.invariants
        }

        # Gather the matches (if any) for this input VBF.
        output_matches_list = []
        matches_list = vbf_dictionary.get("matches", [])
        for match_dict in matches_list:
            match_vbf_obj = build_vbf_from_dict(match_dict)
            match_poly_str = polynomial_to_str(match_vbf_obj.representation.univariate_polynomial)
            compare_types_value = match_dict.get("compare_types", [])
            if isinstance(compare_types_value, set):
                compare_types_value = list(compare_types_value)

            output_matches_list.append({
                "compare_types": compare_types_value,
                "field_n": match_vbf_obj.field_n,
                "irr_poly": match_vbf_obj.irr_poly,
                "poly": match_vbf_obj.representation.univariate_polynomial,
                "poly_str": match_poly_str,
                "invariants": match_vbf_obj.invariants
            })

        output_json_data[f"input_vbf_{input_index}"] = {
            "input_vbf": input_vbf_summary,
            "matches": output_matches_list
        }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_json_data, f, indent=2)


def _export_poly(input_vbf_list: List[Dict[str, Any]], output_file: str):
    # Exports VBF(s) in univariate polynomial representation to a text file.
    if not input_vbf_list:
        click.echo(f"No VBFs to export for --poly to {output_file}")
        return

    first_vbf_object = build_vbf_from_dict(input_vbf_list[0])
    base_dim = first_vbf_object.field_n

    # All VBF(s) must have the same field_n dimension.
    for idx, vbf_dict in enumerate(input_vbf_list):
        vbf_object = build_vbf_from_dict(vbf_dict)
        if vbf_object.field_n != base_dim:
            click.echo(f"Error: VBF #{idx} has field_n={vbf_object.field_n}, expected {base_dim}.")
            click.echo("Aborting --poly export due to mixed dimensions.")
            return

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"{base_dim}\n")
        for vbf_dict in input_vbf_list:
            vbf_object = build_vbf_from_dict(vbf_dict)
            poly_str = polynomial_to_str(vbf_object.representation.univariate_polynomial)
            f.write(f"{poly_str}\n")


def _export_tt(input_vbf_list: List[Dict[str, Any]], output_file: str):
    # Exports VBF(s) in truth table representation to a text file.
    if not input_vbf_list:
        click.echo(f"No VBFs to export for --tt to {output_file}")
        return

    first_vbf_obj = build_vbf_from_dict(input_vbf_list[0])
    base_dim = first_vbf_obj.field_n

    # All VBF(s) must have the same field_n dimension.
    for idx, vbf_dict in enumerate(input_vbf_list):
        vbf_object = build_vbf_from_dict(vbf_dict)
        if vbf_object.field_n != base_dim:
            click.echo(f"Error: VBF #{idx} has field_n={vbf_object.field_n}, expected {base_dim}.")
            click.echo("Aborting --tt export due to mixed dimensions.")
            return

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"{base_dim}\n")
        for vbf_dict in input_vbf_list:
            vbf_object = build_vbf_from_dict(vbf_dict)
            rep = vbf_object.get_truth_table()  # or vbf_obj._get_truth_table_list()
            tt_values = rep.truth_table

            # Write each VBF's truth table on a separate line.
            f.write(" ".join(str(x) for x in tt_values))
            f.write("\n")