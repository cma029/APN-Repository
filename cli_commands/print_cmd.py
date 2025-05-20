import click
from storage.json_storage_utils import load_input_vbfs_and_matches
from cli_commands.cli_utils import format_generic_vbf, build_vbf_from_dict

@click.command("print")
@click.option("--index", "input_vbf_index", default=None, type=int,
              help="If specified, only prints that single index.")
@click.option("--summary", "summary", is_flag=True,
              help="If specified, prints a summary of matches for each VBF.")
@click.option("--input-only", "input_only", is_flag=True,
              help="If specified, only prints the input VBFs.")
def print_cli(input_vbf_index, summary, input_only):
    # Print VBFs and (optionally) their matches from storage/input_vbfs_and_matches.json.
    vbf_dicts = load_input_vbfs_and_matches()
    if not vbf_dicts:
        click.echo("No input VBFs found. Please run 'add-input' first.")
        return

    if summary:
        click.echo("Summary of VBFs and match counts:\n")
        for idx, vbf_dictionary in enumerate(vbf_dicts):
            matches = vbf_dictionary.get("matches", [])
            click.echo(f"  VBF #{idx}: {len(matches)} matches")
        return

    # If no index provided, then print all VBF(s).
    if input_vbf_index is None:
        for idx, vbf_dictionary in enumerate(vbf_dicts):
            if input_only:
                _print_single_vbf_only(vbf_dictionary, idx)
            else:
                _print_single_vbf_with_matches(vbf_dictionary, idx)
    else:
        # If user gave the --index option, then just print that single VBF.
        if input_vbf_index < 0 or input_vbf_index >= len(vbf_dicts):
            click.echo(f"Invalid input VBF index: {input_vbf_index}.")
            return
        vbf_dictionary = vbf_dicts[input_vbf_index]
        if input_only:
            _print_single_vbf_only(vbf_dictionary, input_vbf_index)
        else:
            _print_single_vbf_with_matches(vbf_dictionary, input_vbf_index)

def _print_single_vbf_only(vbf_dict, idx):
    # Prints only the 'input' VBF object.
    vbf_object = build_vbf_from_dict(vbf_dict)
    click.echo(format_generic_vbf(vbf_object, f"\nINPUT VBF {idx}"))
    click.echo("-" * 100)

def _print_single_vbf_with_matches(vbf_dict, index):
    # Prints the 'input' VBF object and then prints all matches below it.
    input_vbf_object = build_vbf_from_dict(vbf_dict)

    click.echo(format_generic_vbf(input_vbf_object, f"\nINPUT VBF {index}"))
    click.echo("-" * 100)

    matches = vbf_dict.get("matches", [])
    click.echo(f"Matches found: {len(matches)}")
    if matches:
        for idx, match_dict in enumerate(matches, start=1):
            compare_types = match_dict.get("compare_types", [])
            matched_object = build_vbf_from_dict(match_dict)

            click.echo(f"  - Matched on {compare_types} with:")
            click.echo("-" * 100)
            click.echo(format_generic_vbf(matched_object, f"Matched VBF #{index}.{idx}"))
            click.echo("-" * 100)
    else:
        click.echo("  - No matches.")