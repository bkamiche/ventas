from fastapi import Request, Depends
from fastapi.templating import Jinja2Templates
from translations import setup_translations, current_language
from auth import get_current_user
import typing
import pytz
from tzlocal import get_localzone
from babel.numbers import format_currency
import constantes

def flash(request: Request, message: typing.Any, category: str = "primary") -> None:
   if "_messages" not in request.session:
       request.session["_messages"] = []
       #request.session["_messages"].append({"category": category, "message": message})
       request.session["_messages"].append((category, message))

def get_flashed_messages(request: Request, with_categories: bool = False):
   #print(request.session)
   return request.session.pop("_messages") if "_messages" in request.session else []

def app_timezone(current_user):
    return pytz.timezone(current_user.user_timezone) if current_user.is_authenticated else get_localzone()

def utc_to_local(utc_dt, current_user, fmt="%Y-%m-%d %H:%M:%S"):
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=pytz.utc)
    return utc_dt.astimezone(app_timezone(current_user)).strftime(fmt)

def app_fc(valor, current_user):
    return format_currency(valor, currency=current_user.moneda, locale=current_user.locale)

def app_fcs(valor, current_user):
    return format_currency(valor, currency='', locale=current_user.locale).strip()

def url_path(request: Request, endpoint: str, **kwargs):
    # Generar la URL completa y extraer el path
    return request.url_for(endpoint, **kwargs)

templates = Jinja2Templates(directory="templates")
templates.env.globals['get_flashed_messages'] = get_flashed_messages
templates.env.globals['current_langage'] = current_language
templates.env.globals['utc_to_local'] = utc_to_local
templates.env.globals['app_fc'] = app_fc
templates.env.globals['app_fcs'] = app_fcs
templates.env.globals['url_path'] = url_path
templates.env.globals.update(
    {k: v for k, v in constantes.__dict__.items() if not k.startswith('_')}
)

def get_templates_with_translations(request):
    _ = setup_translations(request)
    templates.env.globals['_'] = _
    return templates