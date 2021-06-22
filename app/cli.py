"""
Creates command line interfaces for running app utilities.
The interfaces defined here work with pybabel to update language features in the app.
They provide short cuts for the longer commands:
pybabel extract -F babel.cfg -k _l -o messages.pot .
pybabel init -i messages.pot -d app/translations -l es
pybabel update -i messages.pot -d app/translations
pybabel compile -d app/translations


Flask uses Click to create command line interfaces
https://click.palletsprojects.com/en/5.x/
"""

import os
import click


def register(app):
    """
    Register the app with click.
    The current_app variable does not work with click, as these commands are registered 
    at start up, not during the handling of a request. Instead, cli.register(app) is
    called in microblog.py at start up.
    """

    @app.cli.group() # defines root command of various sub-commands
    def translate():
            """
            Translation and localisation commands
            """
            pass


    @translate.command()
    def update():
        """
        Update all languages
        """
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system('pybabel update -i messages.pot -d app/translations'):
            raise RuntimeError('update commend failed')
        os.remove('messages.pot')


    @translate.command()
    def compile():
        """
        Compile all languages
        """
        if os.system('pybabel compile -d app/translations'):
            raise RuntimeError('compile commend failed')


    @translate.command()
    @click.argument('lang')
    def init(lang):
        """
        Initialize a new language
        """
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract commend failed')
        if os.system(
            'pybabel init -i messages.pot -d app/translations -l ' + lang):
            raise RuntimeError('init command faied')
        os.remove('messages.pot')
