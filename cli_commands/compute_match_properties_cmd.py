import click
from typing import List
from storage.json_storage_utils import (
    load_input_apns, save_input_apns,
    load_match_list, save_match_list
)
from apn_properties import compute_apn_properties
from cli_commands.invariants_utils import compute_apn_invariants
from cli_commands.cli_utils import format_generic_apn
from apn_object import APN

@click.command("compute-match-properties")
@click.option("--input-apn-index", default=None, type=int)
def compute_match_properties_cli(input_apn_index):
    # For each APN in the match list (and for its matched APNs), compute properties.
    apn_list = load_input_apns()
    match_list_data = load_match_list()

    if not apn_list:
        click.echo("No APNs in input list. Please run 'add-input' first.")
        return

    if not match_list_data:
        click.echo("No matches available. Please run 'compare' first.")
        return

    def compute_both(apn: APN):
        compute_apn_properties(apn)
        compute_apn_invariants(apn)

    if input_apn_index is None:
        # Process all input APNs.
        for idx, matches in match_list_data.items():
            input_apn = apn_list[idx]
            compute_both(input_apn)

            # Print the input APN.
            click.echo(format_generic_apn(input_apn, f"INPUT_APN {idx}"))
            click.echo("-" * 100)

            if matches:
                # Print each matched APN for this input APN.
                for m_idx, (m_apn, _) in enumerate(matches, start=1):
                    compute_both(m_apn)
                    click.echo(format_generic_apn(m_apn, f"Matched APN #{idx}.{m_idx}"))
                    click.echo("-" * 100)
            else:
                click.echo(f"No matches for Input APN #{idx}.\n")

        save_input_apns(apn_list)
        save_match_list(match_list_data)
        click.echo("Finished computing properties for all matched APNs (and saved updates).")

    else:
        # Process only one input APN (by given index).
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo("Invalid input APN index.")
            return

        if input_apn_index not in match_list_data or not match_list_data[input_apn_index]:
            click.echo("No matches in match-list for this APN index. Run 'compare' first.")
            return

        input_apn = apn_list[input_apn_index]
        matches = match_list_data[input_apn_index]

        compute_both(input_apn)
        click.echo(format_generic_apn(input_apn, f"INPUT_APN {input_apn_index}"))
        click.echo("-" * 100)

        if matches:
            for m_idx, (m_apn, _) in enumerate(matches, start=1):
                compute_both(m_apn)
                click.echo(format_generic_apn(m_apn, f"Matched APN #{input_apn_index}.{m_idx}"))
                click.echo("-" * 100)
        else:
            click.echo(f"No matches for Input APN #{input_apn_index}.\n")

        save_input_apns(apn_list)
        save_match_list(match_list_data)
        click.echo(
            f"Finished computing properties for INPUT_APN {input_apn_index} "
            f"and its matched APNs (and saved updates)."
        )