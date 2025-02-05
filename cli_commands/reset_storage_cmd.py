import os
import click

from apn_storage_pandas import (
    STORAGE_DIR, INPUT_APNS_FILE, MATCH_LIST_FILE, EQUIV_LIST_FILE
)

@click.command("reset-storage")
@click.option("--yes", "-y", is_flag=True)
def reset_storage_cli(yes):
    # Removes input_apns.json, match_list.json, equivalence_list.json from 'storage' folder.
    if not yes:
        click.confirm(
            "Are you sure you want to erase all stored input APNs, match lists, and equivalences? "
            "This action cannot be undone.",
            abort=True
        )

    files_to_delete = [
        INPUT_APNS_FILE,
        MATCH_LIST_FILE,
        EQUIV_LIST_FILE
    ]

    deleted_files = []
    for file in files_to_delete:
        if os.path.isfile(file):
            try:
                os.remove(file)
                deleted_files.append(file)
            except Exception as e:
                click.echo(f"Error deleting {file}: {e}", err=True)

    if deleted_files:
        click.echo(f"Deleted files: {', '.join(deleted_files)}")
    else:
        click.echo("No storage files found to delete.")