import click
import json
from cli_commands.cli_utils import polynomial_to_str
from storage.json_storage_utils import load_input_apns, load_match_list

@click.command("save-matches")
@click.option("--output-file", default="matches_output.json", type=str)
def save_matches_cli(output_file):
    # Exports the current match_list.json contents to a separate output file in JSON format.
    apn_list = load_input_apns()
    match_list_data = load_match_list()

    if not match_list_data:
        click.echo("No matches to save. Please run 'compare' first.")
        return

    output_data = {}
    for idx, matches in match_list_data.items():
        in_apn = apn_list[idx]
        in_apn_poly_str = polynomial_to_str(in_apn.representation.univariate_polynomial)
        in_apn_summary = {
            "field_n": in_apn.field_n,
            "irr_poly": in_apn.irr_poly,
            "poly": in_apn.representation.univariate_polynomial,
            "poly_str": in_apn_poly_str,
            "properties": in_apn.properties,
            "invariants": in_apn.invariants
        }
        matches_list = []
        for match_apn, comp_types in matches:
            match_apn_poly_str = polynomial_to_str(match_apn.representation.univariate_polynomial)
            matches_list.append({
                "compare_types": list(comp_types),
                "field_n": match_apn.field_n,
                "irr_poly": match_apn.irr_poly,
                "poly": match_apn.representation.univariate_polynomial,
                "poly_str": match_apn_poly_str,
                "properties": match_apn.properties,
                "invariants": match_apn.invariants,
            })

        output_data[f"input_apn_{idx}"] = {
            "input_apn": in_apn_summary,
            "matches": matches_list
        }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    click.echo(f"Matches saved to {output_file}")