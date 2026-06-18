from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Alumno(Base):
    __tablename__ = "alumnos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    matricula = Column(String(20), nullable=False, unique=True, index=True)
    carrera = Column(String(20), nullable=False)
    semestre = Column(Integer, nullable=False)

    usuario = relationship("Usuario", back_populates="alumno", uselist=False)


class Maestro(Base):
    __tablename__ = "maestros"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    numero_empleado = Column(String(20), nullable=False, unique=True, index=True)
    materia = Column(String(50), nullable=False)

    usuario = relationship("Usuario", back_populates="maestro", uselist=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False)

    alumno_id = Column(
        Integer,
        ForeignKey("alumnos.id"),
        nullable=True
    )

    maestro_id = Column(
        Integer,
        ForeignKey("maestros.id"),
        nullable=True
    )

    alumno = relationship("Alumno", back_populates="usuario")
    maestro = relationship("Maestro", back_populates="usuario")