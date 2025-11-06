from starlette.requests import Request
from starlette.responses import Response
from babel.dates import get_month_names
from babel.numbers import format_currency
import pytz
from tzlocal import get_localzone
from translations import current_language
import orjson
from fastapi.encoders import jsonable_encoder
from fastapi_cache import Coder
from typing import Any
import base64
import pickle
import hashlib
import re 

class ORJsonCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> bytes:
        try:
            pickle_data = pickle.dumps(value)
            return base64.b64encode(pickle_data)
        except:
            return None

    @classmethod
    def decode(cls, value: bytes) -> Any:
        try:
            #print("decoding")
            return pickle.loads(base64.b64decode(value))
            if '__bytes__' in value:
                return base64.b64decode(value['__bytes__'].encode('utf-8'))
            return orjson.loads(value)
        except:
            return None
    
#def utc_to_local(utc_dt, fmt="%Y-%m-%d %H:%M:%S"):
#    if utc_dt.tzinfo is None:
#        utc_dt = utc_dt.replace(tzinfo=pytz.utc)
#    return utc_dt.astimezone(app_timezone()).strftime(fmt)

#def app_timezone():
#    return pytz.timezone(current_user.user_timezone) if current_user.is_authenticated else get_localzone()

def locale_months(request: Request, abbr=0):
    if abbr == 1:
        meses=get_month_names(locale=current_language(request), width='abbreviated')
    else:
        meses=get_month_names(locale=current_language(request))
    return [meses[i].title() for i in range(1,13)]

def select_locale():
    # Prioriza el idioma en la URL, luego cookies, y finalmente cabeceras del navegador
    return "es"
    #return (
    #    request.args.get('lang') or
    #    request.cookies.get('lang') #or
    #    #request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])
    #)

def app_fc(valor, current_user):
    return format_currency(valor, currency=current_user.moneda, locale=current_user.locale)
    #return format_currency(valor, currency='PEN', locale='es_PE')

def app_fcs(valor, current_user):
    return format_currency(valor, currency='', locale=current_user.locale).strip()
    #return format_currency(valor, currency='', locale='es_PE').strip()

def generar_cache_key(
    func,
    namespace: str = "",
    #*,
    request: Request = None,
    response: Response = None,
    *args,
    **kwargs,
) -> str:
    key=":".join([
        namespace,
        request.cookies.get("access_token","").replace("Bearer ", ""),
        request.cookies.get("lang","es"),
        request.method.lower(),
        request.url.path,
        repr(sorted(request.query_params.items()))
    ])
    key1=namespace+":"+hashlib.md5(key.encode()).hexdigest()
    #print("Key:",key,key1)
    #return "llave"
    #return "llave".encode('utf-8')
    return key1

def validar_password(password):
    #regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,16}$"
    regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,16}$"
    return re.match(regex, password) is not None