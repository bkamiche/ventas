from fastapi import Depends
from sqlalchemy import Enum, Boolean, Column, Integer, String, DateTime, BigInteger, Float, Date, Time, Text, ForeignKey, ForeignKeyConstraint, Table, Index, JSON
from sqlalchemy.orm import relationship, backref, Session
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta, timezone
from database import Base, SessionLocal
import secrets
import hashlib
import uuid
import enum

# Enums
class TipoProducto(enum.Enum):
    SKU = "SKU"
    IMEI = "IMEI"

class StatusVenta(enum.Enum):
    PENDING = "pending"
    VALIDADO = "validado"
    CANCELADO = "cancelado"

# Modelos
class Empresa(Base):
    __tablename__ = 'empresas'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(255), nullable=False, index=True)
    subdominio = Column(String(100), nullable=False, unique=True, index=True)
    tipo_producto = Column(Enum(TipoProducto), nullable=False)
    logo_empresa = Column(String(100), nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    status = Column(Boolean, default=True)
    
    usuarios = relationship("Usuario", back_populates="empresa", cascade="all, delete-orphan")

class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idempresa = Column(Integer, ForeignKey('empresas.id', ondelete='CASCADE'), nullable=False)
    nombre = Column(String(255), nullable=False)
    correo = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    nivel_acceso = Column(String(50), nullable=False)
    yape = Column(String(20), nullable=True)
    cci = Column(String(20), nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    status = Column(Boolean, default=True)
    reset_token = Column(String(120), nullable=True)
    reset_token_expiration = Column(DateTime, nullable=True)
    
    empresa = relationship("Empresa", back_populates="usuarios")
    ventas = relationship("Venta", back_populates="usuario", cascade="all, delete-orphan")

class Venta(Base):
    __tablename__ = 'ventas'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idusuario = Column(Integer, ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    url_imagen = Column(String(500), nullable=False)
    dato_leido = Column(String(255), nullable=False)
    status = Column(Enum(StatusVenta), default=StatusVenta.PENDING)
    puntos = Column(Integer, default=0)
    comision = Column(Integer, default=0)
    descripcion = Column(String(500), nullable=True)
    
    usuario = relationship("Usuario", back_populates="ventas")