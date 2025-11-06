#from fastapi import Depends, HTTPException, status, Request
from fastapi import FastAPI, APIRouter, Query, Request, Depends, HTTPException, status, Form, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy.orm import Session
from models import Usuario
from database import SessionLocal, get_db
from translations import current_language, load_translations
#from templates import flash
from schemas import Token
import hashlib
import os
import typing

class User:
    def __init__(self, usuario: Usuario = None):
        if usuario:
            # Asignar dinámicamente todos los campos del modelo Usuario a la clase User
            self.__dict__.update(usuario.__dict__)
            self.is_authenticated = True  # Usuario autenticado
        else:
            self.is_authenticated = False  # Usuario no autenticado

    def is_authenticated(self):
        return self.is_authenticated

# Configuración de seguridad
SECRET_KEY = os.environ.get('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Contexto de cifrado para contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 para manejar el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Función para verificar la contraseña
def verify_password(plain_password, hashed_password):
    #hashed_password = pwd_context.hash(hashlib.sha256(hashed_password.encode()).hexdigest())
    #hashed_password = hashlib.sha256(hashed_password.encode()).hexdigest()
    #hashed_password = generate_password_hash(hashlib.sha256(user.contrasena.encode()).hexdigest())

    return plain_password == hashed_password
    #return pwd_context.verify(plain_password, hashed_password)

# Función para obtener un usuario por nombre de usuario
def get_user(request: Request, db: Session, username: str):
    idempresa = int(request.state.empresa.id)
    return db.query(Usuario).filter(
        Usuario.correo == username, 
        #Usuario.idempresa==idempresa, 
        or_(Usuario.idempresa==request.state.empresa.id, Usuario.idempresa == 1),
        Usuario.status==True).first()

# Función para autenticar al usuario
def authenticate_user(request: Request, db: Session, username: str, password: str):
    user = get_user(request, db, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

# Función para crear un token JWT
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Función para obtener el usuario actual
def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token","").replace("Bearer ","")  # Obtener el token desde la cookie
    if not token:
        # Si no hay token, devolver un usuario no autenticado
        return User()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            # Si el token no contiene un nombre de usuario, devolver un usuario no autenticado
            return User()
    except JWTError:
        # Si hay un error al decodificar el token, devolver un usuario no autenticado
        return User()
    # Obtener el usuario desde la base de datos
    #usuario = db.query(Usuario).filter(Usuario.usuario == username).first()
    usuario = db.query(Usuario).filter(
        Usuario.correo==username, 
        or_(Usuario.idempresa==request.state.empresa.id, Usuario.idempresa == 1),
        Usuario.status==True).first()
    if not usuario:
        # Si no se encuentra el usuario, devolver un usuario no autenticado
        return User()
    # Devolver una instancia de la clase User con el usuario autenticado
    return User(usuario)

def flash(request: Request, message: typing.Any, category: str = "primary") -> None:
   if "_messages" not in request.session:
       request.session["_messages"] = []
       #request.session["_messages"].append({"category": category, "message": message})
       request.session["_messages"].append((category, message))

def login_required(request: Request):
    lang = current_language(request)
    translation = load_translations(lang)
    _=translation.gettext
    #print(_("Login"))
    flash(request, _('Debe estar conectado para ver este enlace.'), 'error')
    return RedirectResponse(request.url_for('show_login_form'), status_code=303)

#def get_locale(current_user):
#    return current_user.locale if current_user.is_authenticated else 'es_PE'
