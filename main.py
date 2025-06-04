import click
import multiprocessing as mp

try:
    mp.set_start_method("spawn", force=True)
except RuntimeError:
    pass

# Import commands from modules
from cli_commands.add_input_cmd import add_input_cli
from cli_commands.ccz_cmd import ccz_equivalence_cli
from cli_commands.compare_cmd import compare_cli
from cli_commands.compute_input_invariants_cmd import compute_input_invariants_cli
from cli_commands.export_db_html import export_html_cli
from cli_commands.print_cmd import print_cli
from cli_commands.read_db_cmd import read_db
from cli_commands.reset_storage_cmd import reset_storage_cli
from cli_commands.save_to_file_cmd import save_to_file_cli
from cli_commands.store_input_to_db_cmd import store_input_cli
from cli_commands.uni3to1_cmd import uni3to1_equivalence_cli


@click.group()
def cli():
    # CLI interface for handling APNs.
    pass

# Register commands
cli.add_command(add_input_cli)
cli.add_command(ccz_equivalence_cli)
cli.add_command(compare_cli)
cli.add_command(compute_input_invariants_cli)
cli.add_command(export_html_cli)
cli.add_command(print_cli)
cli.add_command(read_db)
cli.add_command(reset_storage_cli)
cli.add_command(save_to_file_cli)
cli.add_command(store_input_cli)
cli.add_command(uni3to1_equivalence_cli)

if __name__ == "__main__":
    cli()