import click
import os
import sys


CONTEXT_SETTINGS = dict(auto_envvar_prefix='IRAIL')

class Context:
    def __init__(self):
        self.terminal_width, self.terminal_height = click.get_terminal_size()


commands_folder = os.path.join(os.path.dirname(__file__), 'commands')
pass_context = click.make_pass_decorator(Context, ensure=True)


class ComplexCLI(click.MultiCommand):
    @staticmethod
    def list_commands(ctx):
        rv = []
        for filename in os.listdir(commands_folder):
            if filename.endswith('.py') and \
               filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    @staticmethod
    def get_command(ctx, name):
        try:
            if sys.version_info[0] == 2:
                name = name.encode('ascii', 'replace')
            mod = __import__('irail.commands.cmd_' + name,
                             None, None, ['cli'])
        except ImportError:
            return
        return mod.cli


@click.command(cls=ComplexCLI, context_settings=CONTEXT_SETTINGS)
@pass_context
def cli(context):
    """
    IRail command line interface
    """
    pass

