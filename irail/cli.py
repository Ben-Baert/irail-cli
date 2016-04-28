import click

TERMINAL_WIDTH, TERMINAL_HEIGHT = click.get_terminal_size()

@click.group()
def cli():
    pass
