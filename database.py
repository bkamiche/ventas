from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import os 
import time
import hashlib

# Configuración de la conexión a MySQL
db_user = os.environ.get('DB_USER')
db_pass = os.environ.get('DB_PASS')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')
DATABASE_URL = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'

# Crear el motor de la base de datos
engine = create_engine(DATABASE_URL, pool_recycle=3600)

# Crear una sesión local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()

def ensure_default_empresa():
    """Asegurar que existe la empresa por defecto"""
    from models import Empresa, TipoProducto, Usuario
    
    db = SessionLocal()
    empresa_default = db.query(Empresa).filter(Empresa.id == 1).first()
    if not empresa_default:
        try:
            nueva_empresa = Empresa(
                id=1,
                nombre="PXL Holding",
                subdominio="", 
                tipo_producto=TipoProducto.SKU,
                status=True,
                logo_empresa='pxl.jpg'
            )
            db.add(nueva_empresa)
            db.commit()
        except Exception as e:
            db.rollback()
            print("Error al crear la empresa por defecto:", e)
    print("Verificando usuario por defecto...")
    user_default = db.query(Usuario).filter(Usuario.id == 1).first()
    if not user_default:
        try:
            pw = "admin123"
            nuevo_usuario = Usuario(
                id=1,
                idempresa=1,
                nombre="Administrador",
                correo="admin@pxlholding.com",
                password=hashlib.sha256(pw.encode()).hexdigest(),
                nivel_acceso="admin",
                yape="",
                cci="",
                fecha_registro=time.strftime('%Y-%m-%d %H:%M:%S'),
                status=True,
            )
            print("Creando usuario por defecto con contraseña:", pw)
            db.add(nuevo_usuario)
            db.commit()
        except Exception as e:
            db.rollback()
            print("Error al crear usuario por defecto:", e)

def get_db():
    db = SessionLocal()
    try:
        # Verificar si la conexión está activa
        db.execute(text("SELECT 1"))  # Consulta simple para verificar la conexión
        ensure_default_empresa()

    except exc.OperationalError as e:
        # Si la conexión está cerrada, intentar reconectar
        print("Error de conexión:", e)
        print("Intentando reconectar...")
        db.close()  # Cerrar la sesión actual
        time.sleep(1)  # Esperar un momento antes de reintentar
        db = SessionLocal()  # Crear una nueva sesión
        try:
            db.execute(text("SELECT 1"))  # Verificar nuevamente la conexión
        except exc.OperationalError as e:
            print("Error al reconectar:", e)
            raise  # Relanzar la excepción si no se puede reconectar
    try:
        yield db
    finally:
        db.close()