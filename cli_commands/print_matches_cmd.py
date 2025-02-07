# print_matches_cmd.py

import click
from storage.json_storage_utils import load_input_apns, load_match_list
from user_input_parser import PolynomialParser

@click.command("print-matches")
@click.option("--input-apn-index", default=None, type=int)
def print_matches_cli(input_apn_index):
    # Prints the contents of match_list.json for either all APNs or a specified index.
    apn_list = load_input_apns()
    match_list_data = load_match_list()

    if not match_list_data:
        click.echo("No match-lists found. Please run 'compare' first.")
        return

    if input_apn_index is None:
        for idx, matches in match_list_data.items():
            in_apn = apn_list[idx]
            click.echo(f"\nINPUT_APN {idx} =>\n{in_apn}")
            click.echo(f"Matches found: {len(matches)}")
            for match_apn, comp_types in matches:
                click.echo(f"  - Matched on {sorted(comp_types)} with:\n{match_apn}")
    else:
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo("Invalid input APN index.")
            return
        if input_apn_index not in match_list_data:
            click.echo(f"No matches exist for INPUT_APN {input_apn_index}.")
            return
        matches = match_list_data[input_apn_index]
        in_apn = apn_list[input_apn_index]
        click.echo(f"\nINPUT_APN {input_apn_index} =>\n{in_apn}")
        click.echo(f"Matches found: {len(matches)}")
        for match_apn, comp_types in matches:
            click.echo(f"  - Matched on {sorted(comp_types)} with:\n{match_apn}")