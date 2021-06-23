"""
Handles translations for the app.
Requires microsofttranslater to be configured.
"""

import json
import requests
from flask_babel import _
from flask import current_app

def translate(text, source_language, dest_language):
    """
    Translates text from the source language to another language.
    -------------------------------------------------------------
    source_language - the source text language, this is determined at time of posting - see main/routes.index
    dest_language - the language of the user
    """

    if 'MS_TRANSLATOR_KEY' not in current_app.config or \
        not current_app.config['MS_TRANSLATOR_KEY']:
        return _('Error: translation service is not configured.')

    auth = {
        'Ocp-Apim-Subscription-Key': current_app.config['MS_TRANSLATOR_KEY'],
        'Ocp-Apim-Subscription-Region': 'westeurope'
    }
    r = requests.post(
        'https://api.cognitive.microsofttranslator.com/'
        '/translate?api-version=3.0&from={}&to={}'.format(
            source_language, dest_language), headers = auth, json=[{'Text': text}]
    )
    if r.status_code != 200:
        return _('Error: the translation service faied.')
    return r.json()[0]['translations'][0]['text']