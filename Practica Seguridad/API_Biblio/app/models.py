from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Libro(Base):
    __tablename__ = "libros"

    id_libro = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    anio_publicacion = Column(Integer, nullable=False)
    paginas = Column(Integer, nullable=False)
    estado = Column(String(20), default="disponible", nullable=False)

    prestamos = relationship("Prestamo", back_populates="libro", cascade="all, delete-orphan")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    rol = Column(String(20), default="usuario", nullable=False)


class Prestamo(Base):
    __tablename__ = "prestamos"

    id_prestamo = Column(Integer, primary_key=True, index=True)
    id_libro = Column(
        Integer,
        ForeignKey("libros.id_libro", ondelete="CASCADE"),
        nullable=False
    )
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False
    )

    libro = relationship("Libro", back_populates="prestamos")
    usuario = relationship("Usuario")
