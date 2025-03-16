import click
from storage.json_storage_utils import load_input_apns_and_matches
from cli_commands.cli_utils import format_generic_apn, build_apn_from_dict

@click.command("print")
@click.option("--index", "input_apn_index", default=None, type=int,
              help="If specified, only prints that single index.")
@click.option("--summary", is_flag=True,
              help="If specified, prints a summary of matches for each APN.")
@click.option("--input-only", is_flag=True,
              help="If specified, only prints the input APNs.")
def print_cli(input_apn_index, summary, input_only):
    # Print APNs and (optionally) their matches from storage/input_apns_and_matches.json.
    apn_dicts = load_input_apns_and_matches()
    if not apn_dicts:
        click.echo("No input APNs found. Please run 'add-input' first.")
        return

    if summary:
        click.echo("Summary of APNs and match counts:\n")
        for idx, apn_dictionary in enumerate(apn_dicts):
            matches = apn_dictionary.get("matches", [])
            click.echo(f"  APN #{idx}: {len(matches)} matches")
        return

    # If no index provided, then print all APN(s).
    if input_apn_index is None:
        for idx, apn_dictionary in enumerate(apn_dicts):
            if input_only:
                _print_single_apn_only(apn_dictionary, idx)
            else:
                _print_single_apn_with_matches(apn_dictionary, idx)
    else:
        # If user gave the --index option, then just print that single APN.
        if input_apn_index < 0 or input_apn_index >= len(apn_dicts):
            click.echo(f"Invalid input APN index: {input_apn_index}.")
            return
        apn_dictionary = apn_dicts[input_apn_index]
        if input_only:
            _print_single_apn_only(apn_dictionary, input_apn_index)
        else:
            _print_single_apn_with_matches(apn_dictionary, input_apn_index)

def _print_single_apn_only(apn_dict, idx):
    # Prints only the 'input' APN object.
    apn_object = build_apn_from_dict(apn_dict)
    click.echo(format_generic_apn(apn_object, f"\nINPUT APN {idx}"))
    click.echo("-" * 100)

def _print_single_apn_with_matches(apn_dict, index):
    # Prints the 'input' APN object and then prints all matches below it.
    input_apn_object = build_apn_from_dict(apn_dict)

    click.echo(format_generic_apn(input_apn_object, f"\nINPUT APN {index}"))
    click.echo("-" * 100)

    matches = apn_dict.get("matches", [])
    click.echo(f"Matches found: {len(matches)}")
    if matches:
        for idx, match_dict in enumerate(matches, start=1):
            compare_types = match_dict.get("compare_types", [])
            matched_object = build_apn_from_dict(match_dict)

            click.echo(f"  - Matched on {compare_types} with:")
            click.echo("-" * 100)
            click.echo(format_generic_apn(matched_object, f"Matched APN #{index}.{idx}"))
            click.echo("-" * 100)
    else:
        click.echo("  - No matches.")