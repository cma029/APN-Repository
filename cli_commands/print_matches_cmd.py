# print_matches_cmd.py

import click
from apn_object import APN
from storage.json_storage_utils import load_input_apns, load_match_list
from cli_commands.cli_utils import format_input_apn, format_matched_apn
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

    if not apn_list:
        click.echo("No input APNs found. Please run 'add-input' first.")
        return

    if input_apn_index is None:
        # Print matches for all input APNs in match_list_data.
        for idx, matches in match_list_data.items():
            _print_input_apn(apn_list[idx], idx)
            click.echo(f"Matches found: {len(matches)}")
            if matches:
                for m_idx, (match_apn, comp_types) in enumerate(matches, start=1):
                    compare_str = sorted(comp_types) 
                    click.echo(f"  - Matched on {compare_str} with:")
                    click.echo("-" * 100)
                    click.echo(format_matched_apn(match_apn, idx, m_idx))
                    click.echo("-" * 100)
            else:
                click.echo("  - No matches.")
    else:
        # Print matches for one specific input APN.
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo("Invalid input APN index.")
            return
        if input_apn_index not in match_list_data:
            click.echo(f"No matches exist for INPUT_APN {input_apn_index}.")
            return
        
        matches = match_list_data[input_apn_index]
        _print_input_apn(apn_list[input_apn_index], input_apn_index)
        click.echo(f"Matches found: {len(matches)}")
        if matches:
            for m_idx, (match_apn, comp_types) in enumerate(matches, start=1):
                compare_str = sorted(comp_types)
                click.echo(f"  - Matched on {compare_str} with:")
                click.echo("-" * 100)
                click.echo(format_matched_apn(match_apn, input_apn_index, m_idx))
                click.echo("-" * 100)
        else:
            click.echo("  - No matches.")

def _print_input_apn(apn: APN, index: int):
    click.echo(f"")
    click.echo(format_input_apn(apn, index))
    click.echo("-" * 100)