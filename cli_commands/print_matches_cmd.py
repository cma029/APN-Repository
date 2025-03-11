import click
from storage.json_storage_utils import load_input_apns_and_matches
from cli_commands.cli_utils import format_generic_apn, build_apn_from_dict

@click.command("print-matches")
@click.option("--index", "input_apn_index", default=None, type=int,
              help="If specified, print matches for only that APN index.")
@click.option("--summary", is_flag=True,
              help="If specified, prints a summary of matches for each APN.")
def print_matches_cli(input_apn_index, summary):
    # Prints matches from storage/input_apns_and_matches.json.
    apn_dicts = load_input_apns_and_matches()
    if not apn_dicts:
        click.echo("No input APNs found. Please run 'add-input' first.")
        return

    if summary:
        click.echo("Summary of APNs and match counts:\n")
        for idx, apn_d in enumerate(apn_dicts):
            matches = apn_d.get("matches", [])
            click.echo(f"  APN #{idx}: {len(matches)} matches")
        return

    if input_apn_index is None:
        # Print matches for all input APNs.
        for idx, apn_d in enumerate(apn_dicts):
            _print_single_apn_matches(apn_d, idx)
    else:
        # Print the matches for one specific input APN.
        if input_apn_index < 0 or input_apn_index >= len(apn_dicts):
            click.echo(f"Invalid input APN index: {input_apn_index}.")
            return
        apn_d = apn_dicts[input_apn_index]
        _print_single_apn_matches(apn_d, input_apn_index)


def _print_single_apn_matches(apn_dict, idx):
    # Convert the dictionary into an APN object (for better formatting).
    input_apn_object = build_apn_from_dict(apn_dict)

    click.echo(format_generic_apn(input_apn_object, f"\nINPUT APN {idx}"))
    click.echo("-" * 100)

    matches = apn_dict.get("matches", [])
    click.echo(f"Matches found: {len(matches)}")
    if matches:
        for i, match_d in enumerate(matches, start=1):
            compare_types = match_d.get("compare_types", [])
            # Convert the matched dictionary into an APN object.
            matched_object = build_apn_from_dict(match_d)

            click.echo(f"  - Matched on {compare_types} with:")
            click.echo("-" * 100)
            click.echo(format_generic_apn(matched_object, f"Matched APN #{idx}.{i}"))
            click.echo("-" * 100)
    else:
        click.echo("  - No matches.")