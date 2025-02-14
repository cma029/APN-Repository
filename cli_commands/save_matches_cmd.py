import click
import json
from cli_commands.cli_utils import polynomial_to_str
from storage.json_storage_utils import load_input_apns_and_matches
from apn_object import APN

@click.command("save-matches")
@click.option("--output-file", default="matches_output.json", type=str,
              help="Where to save the exported matches in JSON format.")
def save_matches_cli(output_file):
    # Exports the current matches for each input APN to a separate JSON file.
    input_apn_list = load_input_apns_and_matches()
    if not input_apn_list:
        click.echo("No input APNs found. Possibly run 'compare' first or add APNs.")
        return

    output_json_data = {}
    for input_index, input_apn_dictionary in enumerate(input_apn_list):
        # Convert this dictionary into an APN object for generating a 'poly_str'.
        input_apn_object = APN(
            input_apn_dictionary["poly"],
            input_apn_dictionary["field_n"],
            input_apn_dictionary["irr_poly"]
        )
        input_apn_object.invariants = input_apn_dictionary.get("invariants", {})

        input_poly_str = polynomial_to_str(input_apn_object.representation.univariate_polynomial)
        # Build a summary dictionary for the main input APN.
        input_apn_summary = {
            "field_n": input_apn_object.field_n,
            "irr_poly": input_apn_object.irr_poly,
            "poly": input_apn_object.representation.univariate_polynomial,
            "poly_str": input_poly_str,
            "invariants": input_apn_object.invariants
        }

        # Gather the matches (if any) for this input APN.
        output_matches_list = []
        matches_list = input_apn_dictionary.get("matches", [])
        for match_apn_dictionary in matches_list:
            # Convert the match dictionary into an APN object.
            match_apn_object = APN(
                match_apn_dictionary["poly"],
                match_apn_dictionary["field_n"],
                match_apn_dictionary["irr_poly"]
            )
            match_apn_object.invariants = match_apn_dictionary.get("invariants", {})

            match_poly_str = polynomial_to_str(match_apn_object.representation.univariate_polynomial)
            compare_types_value = match_apn_dictionary.get("compare_types", [])

            # Ensure 'compare_types' is a list even if originally a set.
            if isinstance(compare_types_value, set):
                compare_types_value = list(compare_types_value)

            output_matches_list.append({
                "compare_types": compare_types_value,
                "field_n": match_apn_object.field_n,
                "irr_poly": match_apn_object.irr_poly,
                "poly": match_apn_object.representation.univariate_polynomial,
                "poly_str": match_poly_str,
                "invariants": match_apn_object.invariants
            })

        output_json_data[f"input_apn_{input_index}"] = {
            "input_apn": input_apn_summary,
            "matches": output_matches_list
        }

    with open(output_file, "w", encoding="utf-8") as output_file_handle:
        json.dump(output_json_data, output_file_handle, indent=2)
    click.echo(f"Matches saved to {output_file}")