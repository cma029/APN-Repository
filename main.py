import click

# Import commands from modules
from cli_commands.add_input_cmd import add_input_cli
from cli_commands.store_input_apns_cmd import store_input_apns_cli

@click.group()
def cli():
    pass

# Register commands
cli.add_command(add_input_cli)
cli.add_command(store_input_apns_cli)

if __name__ == "__main__":
    cli()