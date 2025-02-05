import click

# Import commands from modules
from cli_commands.add_input_cmd import add_input_cli

@click.group()
def cli():
    pass

# Register commands
cli.add_command(add_input_cli)

if __name__ == "__main__":
    cli()