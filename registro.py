from fastapi import FastAPI, APIRouter, Query, Request, Depends, HTTPException, status, Form, BackgroundTasks, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, and_, or_
from auth import get_current_user, get_db
from templates import get_templates_with_translations, current_language, flash
from datetime import datetime, timezone, timedelta
from models import Venta, Usuario, Empresa
from dateutil.relativedelta import relativedelta
from matplotlib import pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from io import BytesIO
from collections import defaultdict, Counter
import numpy as np
from constantes import *
from functions import locale_months, app_fc, generar_cache_key, ORJsonCoder
from auth import login_required
from babel.dates import format_date
from babel import Locale
from translations import setup_translations
from locale import strxfrm
import re
import os
import sys
from typing import Optional, List, Union
from fastapi_pagination import Page, paginate, add_pagination
from urllib.parse import urlencode
import pycountry
from PIL import Image
from openai import OpenAI
import uuid
import json

router = APIRouter()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}  # Extensiones permitidas

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@router.get('/uploads/{filename}')
async def uploaded_file(request: Request, filename: str):
    if os.path.exists(os.environ.get('UPLOAD_FOLDER')+"/"+filename):
        response = FileResponse(os.environ.get('UPLOAD_FOLDER')+"/"+filename)
        response.headers['Cache-Control'] = 'public, max-age=86400' # 1 dia
        expires = datetime.now(timezone.utc) + timedelta(days=1)
        response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        return response
    else:
        response = FileResponse("static/user-icon.png")
        return response

def iter_pages(
    current_page: int,
    total_pages: int,
    left_edge: int = 2,
    left_current: int = 2,
    right_current: int = 2,
    right_edge: int = 2,
) -> List[Optional[int]]:
    """
    Genera una lista de páginas con saltos (usando None para indicar '...').
    La lógica es similar a la que se usa en Flask-SQLAlchemy.
    """
    pages: List[Optional[int]] = []
    last = 0
    for num in range(1, total_pages + 1):
        if num <= left_edge or (
            current_page - left_current <= num <= current_page + right_current
        ) or num > total_pages - right_edge:
            if last + 1 != num:
                pages.append(None)
            pages.append(num)
            last = num
    return pages

@router.api_route(
    '/registro', 
    name="registro",
    methods=["GET", "POST"], 
    response_class=HTMLResponse
)
async def registro(
    request: Request,
    ordenar_por: Optional[str] = Form(default="fecha"),
    orden: Optional[str] = Form(default="asc"),
    page: Optional[int] = Form(1),
    status: Optional[str] = Form(default=""),
    fecha: Optional[str] = Form(default=""),
    userid: Optional[int] = Form(default=None),
    yape: Optional[str] = Form(default=""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user), 
):
    if fecha:
        try:
            fecha = datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            fecha = None
    if not current_user.is_authenticated:
        return login_required(request)
    # Obtener los parámetros de búsqueda del formulario
    usuarios = []
    if current_user.nivel_acceso != 'admin':
        query = db.query(Venta).filter_by(idusuario=current_user.id)  # Filtrar por usuario_id
    else:
        print("por aqui")
        usuarios = db.query(Usuario.id, Usuario.correo).filter(Usuario.idempresa == request.state.empresa.id).all()
        query = db.query(Venta, Usuario.correo, Usuario.yape).join(Usuario).filter(Usuario.idempresa == request.state.empresa.id)
        if userid:
            query = query.filter(Venta.idusuario == userid)  # Filtrar por usuario_id
        if yape:
            query = query.filter(Usuario.yape.ilike(f"%{yape}%"))  # Filtrar por yape
    
    if status:
        query = query.filter(Venta.status == status)  # Filtrar por puntuación

    if fecha:
        fecha_inicio = datetime(fecha.year, fecha.month, fecha.day)
        query = query.filter(Venta.fecha_registro == fecha_inicio)
    # Ordenar la consulta
    if ordenar_por == 'fecha':
        if orden == 'asc':
            query = query.order_by(Venta.fecha_registro.asc())
        else:
            query = query.order_by(Venta.fecha_registro.desc())
    elif ordenar_por == 'usuario':
        if orden == 'asc':
            query = query.order_by(Usuario.correo.asc())
        else:
            query = query.order_by(Usuario.correo.desc())
    elif ordenar_por == 'yape':
        if orden == 'asc':
            query = query.order_by(Usuario.yape.asc())
        else:
            query = query.order_by(Usuario.yape.desc())
    per_page = 12
    offset = (page - 1) * per_page
    # Aplica limit y offset a la consulta
    #print(str(query.statement))
    print(query.statement.compile(compile_kwargs={"literal_binds": True}))
    ventas = query.limit(per_page).offset(offset).all()
    total = query.count()
    total_pages = (total + per_page - 1) // per_page
    # Generar la lista de páginas para iterar en la plantilla
    pages: List[Optional[int]] = iter_pages(page, total_pages)
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("registro.html", 
            {
             "request": request, 
             "current_user": current_user, 
             "ordenar_por": ordenar_por, 
             "orden": orden, 
             "ventas": ventas,
             "status": status, "fecha": fecha, "userid": userid, "yape": yape, "usuarios": usuarios,
             "page": page, "pages": pages, "total_pages": total_pages,
             "logo": request.state.logo_empresa
            })

@router.get('/registro/add')
async def agregar_venta(request: Request, current_user=Depends(get_current_user)):
    if not current_user.is_authenticated:
        return login_required(request)
    templates = get_templates_with_translations(request)
    return templates.TemplateResponse("agregar_registro.html", 
            {"request": request, 
             "current_user": current_user,
             "datetime": datetime, 
             "logo": request.state.logo_empresa
            })

def try_parse_json(text):
    """
    Intenta parsear JSON directamente; si falla, busca un bloque JSON dentro del texto.
    """
    # 1) Texto completo es JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) Extraer bloque JSON entre llaves más externas
    match = re.search(r"(\{[\s\S]*\})", text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None

@router.post('/registro/add')
async def agregar(request: Request,
        fecha_registro: str = Form(...),
        descripcion: str = Form(...),
        foto: UploadFile = File(default=None),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user), 
        _=Depends(setup_translations)
):
    if not current_user.is_authenticated:
        return login_required(request)

    if not descripcion.strip() or not fecha_registro.strip() or not foto or (foto and not allowed_file(foto.filename)):
        flash(request, _('Todos los campos son obligatorios.'), 'error')
        return RedirectResponse(request.url_for('agregar_venta'), status_code=303)

    # Convertir la fecha de registro
    try:
        fecha_registro = datetime.strptime(fecha_registro, '%Y-%m-%d').date()
    except ValueError:
        flash(request, _('Formato de fecha inválido (YYYY-MM-DD).'), 'error')
        return RedirectResponse(request.url_for('agregar_venta'), status_code=303)

    venta = Venta(
        idusuario=current_user.id,
        fecha_registro=fecha_registro,
        descripcion=descripcion.strip(),
        status='pending',
        dato_leido='',
        puntos=0,
        comision=0
    )

    if foto and allowed_file(foto.filename):
        # Guardar la foto original
        #filename = f"{cliente.codigo}.{file.filename.rsplit('.', 1)[1].lower()}"
        filename = f"{request.state.empresa.id}_{current_user.id}_{uuid.uuid4().hex}.{foto.filename.rsplit('.', 1)[1].lower()}"  # Incluir usuario_id en el nombre
        filepath = os.path.join(os.environ.get('UPLOAD_FOLDER'), filename)
        with open(filepath, "wb") as buffer:
            buffer.write(await foto.read())

        # Redimensionar la foto manteniendo la proporción, con el lado menor a 300px
        img = Image.open(filepath)
        if img.width < img.height:
            img.thumbnail((1024, 10000))  # Redimensionar el ancho a 300px
        else:
            img.thumbnail((10000, 1024))  # Redimensionar el alto a 300px

        # Recortar la imagen al centro en un formato cuadrado de 300x300
        ancho_recorte = 1024
        alto_recorte = 1024
        x = (img.width - ancho_recorte) // 2
        y = (img.height - alto_recorte) // 2
        img = img.crop((x, y, x + ancho_recorte, y + alto_recorte))

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        filenametmp = f"/tmp/{uuid.uuid4().hex}.jpg"
        img.save(filenametmp)
        file_id = None
        with open(filenametmp, "rb") as file_content:
            result = client.files.create(
                file=file_content,
                purpose="vision",
            )
            file_id=result.id
        os.remove(filenametmp)

        system_msg = (
            "Eres un asistente experto en extraer datos de imagenes. "
            "RESPONDE únicamente con un JSON válido (sin texto adicional) con las claves: "
            "'sku', 'imei'. "
            "Si no puedes encontrar alguno de los campos, devuelve null para ese campo. "
        )

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                "role": "system", 
                "content": system_msg
                },
                {
                    "role": "user",
                    "content": [
                        {
                        "type": "input_text", 
                        "text": "Extrae número de SKU, IMEI. Devuelve SOLO JSON."},
                        {
                            "type": "input_image",
                            "file_id": file_id,
                        },
                    ],
                }
            ],
        )

        # Reporte de tokens
        usage = getattr(response, "usage", None)

        if usage:
            print("\n📊 Uso de tokens:")
            print(f"  ➤ Prompt tokens:     {usage.input_tokens}")
            print(f"  ➤ Respuesta tokens:  {usage.output_tokens}")
            print(f"  ➤ Total tokens:      {usage.total_tokens}\n")

        print(response.output_text)
        data = try_parse_json(response.output_text)
        if data:
            # Asegurar que las claves existan
            result = {
                "sku": data.get("sku"),
                "imei": data.get("imei"),
            }
            print("Resultado (desde JSON del modelo):")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("No se pudo parsear JSON. Aplicando extracción de respaldo por regex/heurística...")
            result = {
                "sku": "",
                "imei": "",
            }
        if request.state.empresa.tipo_producto == 'SKU':
            venta.dato_leido = result.get("sku") if result.get("sku") else ''
        else:
            venta.dato_leido = result.get("imei") if result.get("imei") else ''
        # Guardar la imagen recortada
        img.save(filepath)

        # Guardar el nombre del archivo en la base de datos
        venta.url_imagen = filename
        db.add(venta)
        db.commit()
    else:
        flash(request, _('No se seleccionó ninguna foto.'))
    return RedirectResponse(request.url_for('registro'), status_code=303)
