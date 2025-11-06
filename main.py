from dotenv import load_dotenv
# Carga las variables del archivo .env
load_dotenv()

from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_cache.backends.memcached import MemcachedBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel
#from starlette.responses import JSONResponse
#from starlette.templating import Jinja2Templates
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.datastructures import URL
from starlette.background import BackgroundTask
from typing import List, Any
#import typing
from sqlalchemy.orm import Session
from sqlalchemy import select
from auth import authenticate_user, create_access_token, get_current_user, get_db
from models import Usuario
#from schemas import Token
from datetime import timedelta, datetime, timezone
from templates import get_templates_with_translations, current_language, flash
from translations import setup_translations
import matplotlib as mpl
import matplotlib.font_manager as fm
import os
import re
import hashlib
from functions import validar_password
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from fastapi.logger import logger as fastapi_logger
import aiomcache
import time
from jose import JWTError, jwt
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GRequest
from typing import Callable
from database import SessionLocal, get_db
import json
import requests
import sys
from registro import router as registro_router

ruta_fuente = './fonts/Poppins/Poppins-Regular.ttf'
fm.fontManager.addfont(ruta_fuente)
fuente_prop = fm.FontProperties(fname=ruta_fuente)
#mpl.rcParams['font.family'] = 'DejaVu Sans'
mpl.rcParams['font.family'] = fuente_prop.get_name()
mpl.rcParams['font.size'] = 10
mpl.rcParams['axes.titlesize'] = 14

if not os.environ.get('SECRET_KEY'):
    #logger.error('No se ha configurado la clave secreta')
    exit(1)

middleware = [
#    Middleware(subdomain_middleware),
    Middleware(SessionMiddleware, secret_key=os.environ.get('SECRET_KEY'))
]

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    #redis = aioredis.from_url("redis://localhost")
    #FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    #FastAPICache.init(SimpleMemoryBackend(), prefix="fastapi-cache")
    backend = MemcachedBackend(aiomcache.Client("127.0.0.1", 11211))
    FastAPICache.init(backend, prefix="fastapi-cache")
    yield

# Configuramos nuestro logger
logger = logging.getLogger("custom.access")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(client_ip)s - %(username)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("/tmp/log.txt")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class CustomAccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        # Aquí extraes la IP real; deberías contar con el proxy_headers activado y forwarded_allow_ips configurado
        client_ip = request.headers.get('X-Forwarded-For', request.client.host)
        # Aquí asumes que ya tienes una forma de autenticarte y extraer el usuario. Por ejemplo:
        username = "anónimo"  # valor por defecto
        token = request.cookies.get("access_token","").replace("Bearer ","")
        SECRET_KEY = os.environ.get('SECRET_KEY')
        ALGORITHM = "HS256"
        try:
            if token:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username: str = payload.get("sub")
        except:
            pass
        # Guardamos la información en el estado para usarla después
        request.state.client_ip = client_ip
        request.state.username = username
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Leer el cuerpo de la solicitud
                body = await request.body()
                request.state.body = body
                # Reconstruir el cuerpo de la solicitud para que esté disponible para las funciones posteriores
                async def reconstruct_body():
                    return body
                request._body = await reconstruct_body()
                # Si es un formulario, también almacenamos los datos parseados
                if "application/x-www-form-urlencoded" in request.headers.get("content-type", ""):
                    form_data = await request.form()
                    request.state.form_data = dict(form_data)
                elif "multipart/form-data" in request.headers.get("content-type", ""):
                    form_data = await request.form()
                    request.state.form_data = dict(form_data)
                else:
                    request.state.form_data = None
            except Exception as e:
                logger.error(f"Error reading request body: {e}")
                request.state.body = None
                request.state.form_data = None
        else:
            request.state.body = None
            request.state.form_data = None
        response = await call_next(request)
        process_time = time.time() - start_time
        # Logueamos la información de la solicitud
        extra = {
            "client_ip": client_ip,
            "username": username
        }
        myurl = request.url.path
        if request.url.query:
            myurl += f"?{request.url.query}"
        if request.state.form_data:
            form_str = ", ".join([f"{key}:{value}" for key, value in request.state.form_data.items()])
            myurl += f" | Form: {form_str}"
        logger.info(f'"{request.method} {myurl}" {response.status_code} {process_time:.2f}s', extra=extra)
        return response

app = FastAPI(middleware=middleware, lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(CustomAccessLogMiddleware)
app.include_router(registro_router)

#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')  # Include timestamp
#logger = logging.getLogger(__name__)

# Configuración
ROOT_DOMAIN = os.getenv("ROOT_DOMAIN", "tudominio.com")  # Cambia por tu dominio principal

def is_html_request(request: Request) -> bool:
    """Determina si es una request que probablemente devuelve HTML"""
    accept = request.headers.get("accept", "").lower()
    path = request.url.path.lower()
    
    # Si específicamente pide HTML
    if "text/html" in accept:
        return True
    
    # Si es un path raíz o de página (sin extensión)
    if '/' == path or path.endswith('/') or '.' not in path.split('/')[-1]:
        return True
    
    return False

@app.middleware("http")
async def subdomain_middleware(request: Request, call_next):
    from models import Empresa

    if not is_html_request(request):
        return await call_next(request)
    # Obtener el host de la solicitud
    host = request.headers.get("host", "")
    print("Host recibido:", host)
    # Extraer subdominio usando regex
    subdomain_match = re.match(r'^(?:https?://)?([^\.]+)\.', host)
    print("Subdominio extraído:", subdomain_match.group(1) if subdomain_match else "Ninguno")
    request.state.empresa = Empresa(id=1)
    request.state.subdomain = ""
    request.state.logo_empresa = "logoPXL.png"

    if subdomain_match:
        subdomain = subdomain_match.group(1).lower()
        
        # Ignorar subdominios comunes que no son empresas
        ignored_subdomains = ['www', 'app', 'api', 'admin', 'test', 'staging','ventas']
        
        if subdomain not in ignored_subdomains:
            # Validar subdominio en la base de datos
            try:
                
                db: Session = SessionLocal()
                empresa = db.query(Empresa).filter(
                    Empresa.subdominio == subdomain,
                    Empresa.status == True
                ).first()
                
                if not empresa:
                    # Redirigir al dominio principal si el subdominio no existe o está inactivo
                    redirect_url = f"http://{ROOT_DOMAIN}"
                    return RedirectResponse(url=redirect_url, status_code=302)
                
                # Agregar la empresa al estado de la request para usarlo en los endpoints
                request.state.empresa = empresa
                request.state.subdomain = subdomain
                request.state.logo_empresa = empresa.logo_empresa
                
            except Exception as e:
                # En caso de error, redirigir al dominio principal
                print(f"Error validando subdominio: {e}")
                redirect_url = f"http://{ROOT_DOMAIN}"
                return RedirectResponse(url=redirect_url, status_code=302)
    
    # Si no hay subdominio o es uno de los ignorados, continuar
    response = await call_next(request)
    return response

@app.middleware("http")
async def set_base_url(request: Request, call_next):
    # Obtener el esquema (HTTP o HTTPS) del proxy
    scheme = request.headers.get("X-Forwarded-Proto", "http")
    mhost = request.headers.get('host', request.client.host)
    # Construir la URL base
    base_url = URL(f"{scheme}://{mhost}")
    # Crear un nuevo objeto Request con la URL base correcta
    new_request = Request(
        scope={
            **request.scope,
            "type": request.scope["type"],
            "scheme": base_url.scheme,
            "server": (base_url.hostname, request.url.port),
            "root_path": request.scope["root_path"],
        }
    )
    # Pasar el nuevo objeto Request a call_next
    response = await call_next(new_request)
    return response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    csp_policy = \
        "default-src 'self'; "+\
        "script-src 'self' 'unsafe-inline' data: https://code.jquery.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "+\
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "+\
        "object-src 'none'; "+\
        "base-uri 'self'; "+\
        "worker-src 'self' blob:; "+\
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "+\
        "img-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com data:; "+\
        "frame-ancestors 'none';"
    response.headers['Content-Security-Policy'] = csp_policy
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    return response

# Montar archivos estáticos
#app.mount("/static", StaticFiles(directory="static"), name="static")

conf = ConnectionConfig(
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD'),
    MAIL_FROM = os.environ.get('MAIL_FROM'),
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465)),
    MAIL_SERVER = os.environ.get('MAIL_SERVER'),
    MAIL_STARTTLS = False,
    MAIL_SSL_TLS = True,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True,
    MAIL_FROM_NAME=os.environ.get('MAIL_FROMNAME'),
)

def path_for(self, name: str, **path_params: Any) -> str:
    """
    Genera solo el path de la ruta, sin el host ni el esquema.
    """
    url = super(Request, self).url_for(name, **path_params)
    return url.path  # Devolver solo el atributo path del objeto URL

# Reemplazar la función url_for en el objeto Request
Request.url_for = path_for

#@app.on_event("startup")
#async def startup():
#    FastAPICache.init(SimpleMemoryBackend(), prefix="fastapi-cache")
#    #mc = MemcachedBackend(endpoint="127.0.0.1", port=11211)  # Reemplaza con la dirección de tu servidor Memcached
#    #FastAPICache.init(mc, prefix="fastapi-cache")

@app.exception_handler(404)
async def pagina_no_encontrada(request: Request, exc: HTTPException):
    #print(request)
    if request.url.path.endswith('.jpg'):
        # Ruta a tu imagen JPG por defecto
        response = FileResponse("static/user-icon.png", status_code=404)
        return response
    else:
        templates = get_templates_with_translations(request)
        return templates.TemplateResponse("404.html", {"request": request, "current_language": current_language(request)}, status_code=404)

@app.get('/static/{path}')
async def static(path):
    response = FileResponse("static/"+path)
    if not path.endswith('.css') and not path.endswith('.js'):
        response.headers['Cache-Control'] = 'public, max-age=31536000' # Example for 365 days
        # or you can set expires
        expires = datetime.now(timezone.utc) + timedelta(days=365)
        response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return response

#app.mount("/mystatic", StaticFiles(directory="mystatic"), name="mystatic")

@app.post("/set_language/{lang}")
@app.get("/set_language/{lang}")
async def change_language(request: Request, lang: str):
    response = RedirectResponse(request.headers.get("referer") or '/', status_code=303)
    response.set_cookie(key="lang", value=lang)
    return response

def login_required(request: Request, _=Depends(setup_translations)):
    print("Se va al login")
    flash(request, _('Debe estar conectado para ver este enlace.'), 'error')
    return RedirectResponse(request.url_for('show_login_form'), status_code=303)


# Guardar el estado temporalmente (usualmente se almacena en DB o sesión)
oauth_states = {}

@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt():
        return """
User-agent: *
Disallow: /admin/
Disallow: /api/
Disallow: /dashboard/
Allow: /
"""

@app.get("/login", response_class=HTMLResponse)
async def show_login_form(request: Request):
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("login.html", {"request": request, "current_language": current_language(request), "logo": request.state.logo_empresa})

# Endpoint para procesar el formulario de login
@app.get("/login/{userid}")
async def login_withid(
    request: Request, 
    userid: int, 
    db: Session = Depends(get_db),
    _=Depends(setup_translations), 
    current_user=Depends(get_current_user)
):
    if userid:
        if current_user.is_authenticated and current_user.id == 1:
            user = db.query(Usuario).filter_by(id=userid).first()
            if user:
                return login(request, user.usuario, hashlib.sha256(user.password.encode()).hexdigest(), db, _)
                #return RedirectResponse(request.url_for('customers'), status_code=303)
    return RedirectResponse(request.url_for('show_login_form'), status_code=303)

@app.post("/login")
def login(
    request: Request,
    usuario: str = Form(...),
    contrasena: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(setup_translations)
):
    print(usuario, contrasena)
    user = authenticate_user(request, db, usuario, contrasena)
    if user:
        access_token_expires = timedelta(minutes=10080)
        access_token = create_access_token(
            data={"sub": user.correo}, expires_delta=access_token_expires
        )
        print("se ha creado el access_token "+access_token)
        user = db.query(Usuario).filter_by(correo=usuario).first()
        user.fec_lastlogin = datetime.now(timezone.utc)
        db.commit()
        # Redirigir al usuario a una página de éxito o dashboard
        response = RedirectResponse(request.url_for("registro"), status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    else:
        templates = get_templates_with_translations(request)
        flash(request, _('Credenciales inválidas o usuario inactivo'))
        return templates.TemplateResponse("login.html", {"request": request, "current_language": current_language(request), "logo": request.state.logo_empresa})
    return response

@app.get("/logout")
async def logout(request: Request):
    # Crear una respuesta de redirección
    response = RedirectResponse(url="/", status_code=303)
    # Eliminar la cookie de autenticación
    response.delete_cookie(key="access_token")  # Cambia "access_token" por el nombre de tu cookie
    return response

@app.get('/recover-password')
async def recuperar_password_form(request: Request):
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("recuperar_clave.html", {"request": request, "current_language": current_language(request), "logo": request.state.logo_empresa})

@app.post('/recover-password')
async def recuperar_clave(request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(setup_translations)):
    usuario = db.query(Usuario).filter_by(correo=email).first()
    if usuario and usuario.id!=1:
        usuario.generar_token_recuperacion(db)
        enlace_recuperacion = str(request.base_url).rstrip("/") + request.url_for('cambiar_clave_form', token=usuario.reset_token)
        message = MessageSchema(
            subject=_('Recuperación de contraseña'),
            recipients=[usuario.email],
            headers={"From": os.environ.get('MAIL_FROM'), "Reply-To": os.environ.get('MAIL_FROM')},
            body=_("""
¡Hola!

Parece que olvidaste tu contraseña. No te preocupes, ¡pasa a menudo!

Para volver a acceder a tu cuenta, simplemente haz clic en el siguiente enlace:

{enlace}

Este enlace caducará en 1 hora. Si no solicitaste este cambio, no es necesario que hagas nada.

Si tienes alguna pregunta, no dudes en contactarnos.

Saludos,
El equipo de soporte
""").format(enlace=enlace_recuperacion), 
            subtype=MessageType.plain)
        fm = FastMail(conf)
        await fm.send_message(message)
        flash(request, _('Se ha enviado un enlace de recuperación a tu correo.'), 'info')
    else:
        flash(request, _('No se encontró una cuenta con ese correo.'), 'error')
    return RedirectResponse(request.url_for('show_login_form'), status_code=303)

@app.get('/change-password/{token}')
async def cambiar_clave_form(request: Request, token: str, db: Session = Depends(get_db), _=Depends(setup_translations)):
    usuario = db.query(Usuario).filter_by(reset_token=token).first()
    if not usuario or not usuario.verificar_token_recuperacion(token):
        flash(request, _('El enlace de recuperación es inválido o ha expirado.'), 'error')
        return RedirectResponse(request.url_for('show_login_form'), status_code=303)
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("cambiar_clave.html", {"request": request, "token": token, "logo": request.state.logo_empresa})

@app.post('/change-password/{token}')
async def cambiar_clave(request: Request,
    token: str,
    nueva_clave: str = Form(...),
    confirmar_clave: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(setup_translations)):
    usuario = db.query(Usuario).filter_by(reset_token=token).first()
    if not usuario or not usuario.verificar_token_recuperacion(token):
        flash(request, _('El enlace de recuperación es inválido o ha expirado.'), 'error')
        return RedirectResponse(request.url_for('show_login_form'), status_code=303)
    print(nueva_clave, confirmar_clave)
    if nueva_clave != confirmar_clave:
        flash(request, _('Las contraseñas no coinciden.'), 'error')
    elif not validar_password(nueva_clave):
        flash(request, _('La contraseña debe tener entre 8 y 16 caracteres, incluir letras mayúsculas, minúsculas, números y un símbolo.'), 'error')
    else:
        #usuario.password = generate_password_hash(nueva_clave)
        usuario.password = nueva_clave
        usuario.reset_token = None
        usuario.reset_token_expiration = None
        db.commit()
        flash(request, _('Tu contraseña ha sido actualizada.'), 'success')
        return RedirectResponse(request.url_for('show_login_form'), status_code=303)
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("cambiar_clave.html", {"request": request, "token": token, "logo": request.state.logo_empresa})

@app.get("/privacy")
async def privacy(request: Request):
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("privacy.html", {"request": request, "logo": request.state.logo_empresa})

@app.get("/about")
async def about(request: Request):
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("about.html", {"request": request, "logo": request.state.logo_empresa})

@app.get("/que-hacemos")
async def whatwedo(request: Request):
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("what-we-do.html", {"request": request, "logo": request.state.logo_empresa})

@app.get("/tos")
async def tos(request: Request):
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("tos.html", {"request": request, "logo": request.state.logo_empresa})

@app.get("/")
async def index(
    request: Request, 
    _=Depends(setup_translations), 
    current_user=Depends(get_current_user)
):
    templates = get_templates_with_translations(request)
    if not current_user.is_authenticated:
        return RedirectResponse(request.url_for('login'), status_code=303)  
    else:
        return RedirectResponse(request.url_for('registro'), status_code=303)  

    return templates.TemplateResponse("main.html", {"request": request, "current_user": current_user, "logo": request.state.logo_empresa})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, proxy_headers=True, forwarded_allow_ips="*")
