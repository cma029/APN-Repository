# compute_match_properties_cmd.py

import click
from apn_storage_pandas import (
    load_input_apns, save_input_apns,
    load_match_list, save_match_list
)
from apn_properties import compute_apn_properties
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

    def compute_for_apn(apn: APN):
        compute_apn_properties(apn)
        click.echo(f"Computed properties for:\n{apn}")

    if input_apn_index is None:
        for idx, matches in match_list_data.items():
            input_apn = apn_list[idx]
            compute_for_apn(input_apn)
            for (m_apn, _) in matches:
                compute_for_apn(m_apn)
        save_input_apns(apn_list)
        save_match_list(match_list_data)
        click.echo("Finished computing properties for all matched APNs (and saved updates).")
    else:
        if input_apn_index < 0 or input_apn_index >= len(apn_list):
            click.echo("Invalid input APN index.")
            return
        if input_apn_index not in match_list_data or not match_list_data[input_apn_index]:
            click.echo("No matches in match-list for this APN index. Run 'compare' first.")
            return

        input_apn = apn_list[input_apn_index]
        matches = match_list_data[input_apn_index]

        compute_for_apn(input_apn)
        for (m_apn, _) in matches:
            compute_for_apn(m_apn)

        save_input_apns(apn_list)
        save_match_list(match_list_data)
        click.echo(
            f"Finished computing properties for INPUT_APN {input_apn_index} "
            f"and its matched APNs (and saved updates)."
        )