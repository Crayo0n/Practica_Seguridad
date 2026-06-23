from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, ConfigDict

AÑO_ACTUAL = datetime.now().year


class EstadoLibro(str, Enum):
    disponible = "disponible"
    prestado = "prestado"


class Usuario(BaseModel):
    id: int = Field(..., gt=0, description="Identificador de usuario", example=1)
    nombre: str = Field(..., min_length=2, max_length=50, description="Nombre del usuario")
    correo: EmailStr = Field(..., description="Correo electrónico válido")

    model_config = ConfigDict(from_attributes=True)


class Libro(BaseModel):
    id_libro: int = Field(..., gt=0, description="Identificador de libro", example=1)
    nombre: str = Field(..., min_length=2, max_length=100)
    anio_publicacion: int = Field(..., gt=1450, le=AÑO_ACTUAL)
    paginas: int = Field(..., gt=1)
    estado: EstadoLibro = Field(default=EstadoLibro.disponible)

    model_config = ConfigDict(from_attributes=True)


class Prestamo(BaseModel):
    id_prestamo: int | None = Field(default=None, description="Identificador de Prestamo (opcional)", example=1)
    id_libro: int
    usuario_id: int

    model_config = ConfigDict(from_attributes=True)


class PrestamoResponse(BaseModel):
    id_prestamo: int
    id_libro: int
    nombre_libro: str
    usuario_id: int
    correo_usuario: str

    model_config = ConfigDict(from_attributes=True)


class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    rol: str = Field(default="usuario", pattern="^(usuario|admin)$")


class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    email: str
    rol: str

    model_config = ConfigDict(from_attributes=True)
