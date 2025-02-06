import click

# Import commands from modules
from cli_commands.add_input_cmd import add_input_cli
from cli_commands.ccz_cmd import ccz_equivalence_cli
from cli_commands.compare_cmd import compare_apns_cli
from cli_commands.print_matches_cmd import print_matches_cli
from cli_commands.read_field_cmd import read_db_apns
from cli_commands.reset_storage_cmd import reset_storage_cli
from cli_commands.save_matches_cmd import save_matches_cli
from cli_commands.store_input_apns_cmd import store_input_apns_cli


@click.group()
def cli():
    pass

# Register commands
cli.add_command(add_input_cli)
cli.add_command(ccz_equivalence_cli)
cli.add_command(compare_apns_cli)
cli.add_command(print_matches_cli)
cli.add_command(read_db_apns)
cli.add_command(reset_storage_cli)
cli.add_command(save_matches_cli)
cli.add_command(store_input_apns_cli)

if __name__ == "__main__":
    cli()