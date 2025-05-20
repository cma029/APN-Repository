import click
from pathlib import Path

@click.command("reset-storage")
@click.option("--yes", "-y", is_flag=True)
def reset_storage_cli(yes):
    """
    Removes all stored files for VBFs and equivalences:
      - storage/input_vbfs_and_matches.json
      - storage/equivalence_list.json
    """
    if not yes:
        click.confirm(
            "Are you sure you want to erase all stored VBFs and equivalences? "
            "This action cannot be undone.",
            abort=True
        )

    storage_dir = Path("storage")
    input_vbfs_and_matches_file = storage_dir / "input_vbfs_and_matches.json"
    equivalence_list_file = storage_dir / "equivalence_list.json"

    files_to_delete = [input_vbfs_and_matches_file, equivalence_list_file]

    deleted_paths = []
    for file_path in files_to_delete:
        if file_path.is_file():
            try:
                file_path.unlink()  # Remove the file.
                deleted_paths.append(file_path)
            except Exception as exc:
                click.echo(f"Error deleting {file_path}: {exc}", err=True)

    if deleted_paths:
        path_strings = [str(path) for path in deleted_paths]
        click.echo(f"Deleted files: {', '.join(path_strings)}")
    else:
        click.echo("No storage files found to delete.")