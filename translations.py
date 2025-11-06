import gettext
from fastapi import Request

BABEL_SUPPORTED_LOCALES = ['en','es','pt','fr','it','de']

def load_translations(lang: str):
    return gettext.translation('messages', localedir='translations', languages=[lang])

def current_language(request: Request):
    return (
        request.cookies.get('lang', 'es')
    )

def setup_translations(request: Request):
    lang = current_language(request)
    translation = load_translations(lang)
    return translation.gettext