import os
import click

# Flask uses Click to create command line interfaces
# https://click.palletsprojects.com/en/5.x/

def register(app):

    @app.cli.group()
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


# pybabel extract -F babel.cfg -k _l -o messages.pot .
# pybabel init -i messages.pot -d app/translations -l es
# pybabel update -i messages.pot -d app/translations
# pybabel compile -d app/translations