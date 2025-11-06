from dotenv import load_dotenv
# Carga las variables del archivo .env
load_dotenv()

from database import engine, Base
from models import *

# Crear todas las tablas definidas en los modelos
def create_tables():
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("¡Tablas creadas exitosamente!")

if __name__ == "__main__":
    create_tables()