import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func
import bcrypt
from jose import jwt, JWTError

from app.database import get_db
from app import models
from app import schemas

app = FastAPI(
    title="API de Biblioteca Digital v4",
    description="Versión 4: API de biblioteca protegida con API Key, JWT, Roles (RBAC) y prevención BOLA/IDOR",
    version="4.0"
)

# Configuración de Seguridad
API_KEY_VALIDA = os.getenv("API_KEY", "BIBLIO123")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "BIBLIO_JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Request schema para Login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Helper para verificar contraseñas
def verificar_password(plain_password: str, hashed_password: str) -> bool:
    if isinstance(hashed_password, str):
        if hashed_password.startswith("$2y$"):
            hashed_password = hashed_password.replace("$2y$", "$2b$", 1)
        hashed_password_bytes = hashed_password.encode("utf-8")
    else:
        hashed_password_bytes = hashed_password
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password_bytes)


# Helper para crear tokens JWT
def crear_token_acceso(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


# Dependencia: Validar API Key
def validar_api_key(x_api_key: str | None = Header(default=None, alias="x-api-key")):
    if x_api_key != API_KEY_VALIDA:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "No autorizado",
                "mensaje": "API Key inválida o no enviada"
            }
        )
    return True


# Dependencia: Validar JWT y obtener usuario actual
def obtener_usuario_actual(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
) -> models.Usuario:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "No autorizado",
                "mensaje": "Falta el token de sesión (JWT) en la cabecera Authorization"
            }
        )
    
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "No autorizado",
                    "mensaje": "Formato de token inválido. Debe ser Bearer <token>"
                }
            )
        token = parts[1]
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "No autorizado",
                    "mensaje": "Token inválido: falta información de identidad"
                }
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "No autorizado",
                "mensaje": "Token JWT inválido o expirado"
            }
        )
        
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "No autorizado",
                "mensaje": "El usuario asociado a este token ya no existe"
            }
        )
    return usuario


# Dependencia para verificar roles (RBAC)
def requiere_rol(*roles_permitidos):
    def dependencia(usuario_actual: models.Usuario = Depends(obtener_usuario_actual)):
        if usuario_actual.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Acceso denegado",
                    "mensaje": "No tienes el rol necesario para esta acción"
                }
            )
        return usuario_actual
    return dependencia


# Endpoint: Iniciar Sesión (Login)
@app.post("/login")
def login(
    credentials: LoginRequest,
    api_key_valida: bool = Depends(validar_api_key),
    db: Session = Depends(get_db)
):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == credentials.email).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "No autorizado",
                "mensaje": "Correo o contraseña incorrectos"
            }
        )
    
    if not verificar_password(credentials.password, usuario.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "No autorizado",
                "mensaje": "Correo o contraseña incorrectos"
            }
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = crear_token_acceso(
        data={"sub": usuario.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol
        }
    }


# Endpoint: Obtener Perfil del Usuario Autenticado
@app.get("/api/perfil")
def obtener_perfil(
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual)
):
    return {
        "id": usuario_actual.id,
        "nombre": usuario_actual.nombre,
        "email": usuario_actual.email,
        "rol": usuario_actual.rol
    }


# Registrar un nuevo libro (Solo Admin)
@app.post("/libros", status_code=status.HTTP_201_CREATED)
def registrar_libro(
    libro: schemas.Libro,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(requiere_rol("admin")),
    db: Session = Depends(get_db)
):
    db_libro = (
        db.query(models.Libro)
        .filter(models.Libro.id_libro == libro.id_libro)
        .first()
    )

    if db_libro:
        raise HTTPException(status_code=400, detail="El id_libro ya existe")

    nuevo_libro = models.Libro(
        id_libro=libro.id_libro,
        nombre=libro.nombre,
        anio_publicacion=libro.anio_publicacion,
        paginas=libro.paginas,
        estado=libro.estado.value
    )

    db.add(nuevo_libro)
    db.commit()
    db.refresh(nuevo_libro)

    return {"mensaje": "Libro registrado con éxito", "libro": schemas.Libro.model_validate(nuevo_libro)}


# Listar todos los libros Disponibles (Cualquier usuario autenticado)
@app.get("/libros", response_model=list[schemas.Libro])
def listar_libros_disponibles(
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    libros = (
        db.query(models.Libro)
        .filter(models.Libro.estado == schemas.EstadoLibro.disponible.value)
        .all()
    )
    return libros


# Buscar un libro por su nombre (Cualquier usuario autenticado)
@app.get("/libros/{nombre}", response_model=schemas.Libro)
def buscar_libro(
    nombre: str,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    libro = (
        db.query(models.Libro)
        .filter(func.lower(models.Libro.nombre) == nombre.lower())
        .first()
    )

    if not libro:
        raise HTTPException(status_code=404, detail="Libro no encontrado en la biblioteca")

    return libro


# Registrar un nuevo préstamo (Protección BOLA: Un usuario normal sólo puede pedir préstamos para sí mismo)
@app.post("/prestamos", status_code=status.HTTP_201_CREATED)
def prestar_libro(
    prestamo: schemas.Prestamo,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    # Protección BOLA/IDOR: Verificar si el usuario intenta crear un préstamo para otra persona
    if usuario_actual.rol != "admin" and prestamo.usuario_id != usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Acceso denegado",
                "mensaje": "No tienes permiso para solicitar préstamos en nombre de otro usuario"
            }
        )

    # Verificar si el id_prestamo ya existe
    db_prestamo = (
        db.query(models.Prestamo)
        .filter(models.Prestamo.id_prestamo == prestamo.id_prestamo)
        .first()
    )

    if db_prestamo:
        raise HTTPException(status_code=400, detail="El id_prestamo ya existe")

    # Verificar si el usuario a prestar existe en la BD
    usuario_encontrado = (
        db.query(models.Usuario)
        .filter(models.Usuario.id == prestamo.usuario_id)
        .first()
    )

    if not usuario_encontrado:
        raise HTTPException(status_code=404, detail="Usuario del préstamo no encontrado")

    # Buscar el libro
    libro_encontrado = (
        db.query(models.Libro)
        .filter(models.Libro.id_libro == prestamo.id_libro)
        .first()
    )

    if not libro_encontrado:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    if libro_encontrado.estado == schemas.EstadoLibro.prestado.value:
        raise HTTPException(status_code=409, detail="Conflicto: El libro ya está prestado")

    # Marcar libro como prestado
    libro_encontrado.estado = schemas.EstadoLibro.prestado.value

    # Crear el préstamo
    nuevo_prestamo = models.Prestamo(
        id_prestamo=prestamo.id_prestamo,
        id_libro=prestamo.id_libro,
        usuario_id=prestamo.usuario_id
    )

    db.add(nuevo_prestamo)
    db.commit()
    db.refresh(nuevo_prestamo)

    # Construir respuesta enriquecida
    response_data = schemas.PrestamoResponse(
        id_prestamo=nuevo_prestamo.id_prestamo,
        id_libro=nuevo_prestamo.id_libro,
        nombre_libro=libro_encontrado.nombre,
        usuario_id=nuevo_prestamo.usuario_id,
        correo_usuario=usuario_encontrado.email
    )

    return {"mensaje": "Préstamo exitoso", "prestamo": response_data}


# Marcar un libro como devuelto (Protección BOLA: Sólo el dueño del préstamo o admin pueden devolverlo)
@app.put("/libros/{id_libro}/devolver", status_code=status.HTTP_200_OK)
def devolver_libro(
    id_libro: int,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    libro_encontrado = (
        db.query(models.Libro)
        .filter(models.Libro.id_libro == id_libro)
        .first()
    )

    if not libro_encontrado:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    # Buscar préstamo activo para el libro
    prestamo_activo = (
        db.query(models.Prestamo)
        .filter(models.Prestamo.id_libro == id_libro)
        .first()
    )

    # Protección BOLA/IDOR: Verificar si el libro está prestado a otro usuario
    if prestamo_activo and usuario_actual.rol != "admin" and prestamo_activo.usuario_id != usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Acceso denegado",
                "mensaje": "No tienes permiso para devolver un libro que fue prestado a otro usuario"
            }
        )

    libro_encontrado.estado = schemas.EstadoLibro.disponible.value
    db.commit()

    return {"mensaje": "Libro devuelto con éxito. Estado 200 OK."}


# Eliminar el registro de un préstamo (Protección BOLA: Sólo el dueño del préstamo o admin pueden eliminarlo)
@app.delete("/prestamos/{id_prestamo}")
def eliminar_prestamo(
    id_prestamo: int,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    prestamo_encontrado = (
        db.query(models.Prestamo)
        .filter(models.Prestamo.id_prestamo == id_prestamo)
        .first()
    )

    if not prestamo_encontrado:
        raise HTTPException(status_code=404, detail="Registro de préstamo no encontrado")

    # Protección BOLA/IDOR: Verificar si el préstamo a eliminar pertenece a otro usuario
    if usuario_actual.rol != "admin" and prestamo_encontrado.usuario_id != usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Acceso denegado",
                "mensaje": "No tienes permiso para eliminar el registro de préstamo de otro usuario"
            }
        )

    db.delete(prestamo_encontrado)
    db.commit()

    return {"mensaje": "Registro de préstamo eliminado correctamente"}


# -----------------------------------------------------------------------------
# RUTAS DE PRUEBA Y DEMOSTRACIÓN DE BOLA/IDOR
# -----------------------------------------------------------------------------

# Ruta vulnerable (Demo BOLA): permite obtener cualquier préstamo sin validar propiedad
@app.get("/api/vulnerable/prestamos/{id_prestamo}")
def obtener_prestamo_vulnerable(
    id_prestamo: int,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    prestamo = (
        db.query(models.Prestamo)
        .filter(models.Prestamo.id_prestamo == id_prestamo)
        .first()
    )

    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    return {
        "advertencia": "Esta ruta es vulnerable a BOLA/IDOR",
        "explicacion": "Valida API Key y JWT, pero no valida si el préstamo solicitado pertenece al usuario autenticado o si es administrador.",
        "usuario_autenticado": {
            "id": usuario_actual.id,
            "nombre": usuario_actual.nombre,
            "rol": usuario_actual.rol
        },
        "datos": {
            "id_prestamo": prestamo.id_prestamo,
            "id_libro": prestamo.id_libro,
            "usuario_id": prestamo.usuario_id
        }
    }


# Ruta segura (Protegida contra BOLA): solo permite ver si pertenece al usuario o es admin
@app.get("/api/prestamos/{id_prestamo}")
def obtener_prestamo_seguro(
    id_prestamo: int,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    prestamo = (
        db.query(models.Prestamo)
        .filter(models.Prestamo.id_prestamo == id_prestamo)
        .first()
    )

    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    # Validación BOLA/IDOR
    if usuario_actual.rol != "admin" and prestamo.usuario_id != usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Acceso denegado",
                "mensaje": "No tienes permiso para consultar un préstamo que pertenece a otro usuario"
            }
        )

    return {
        "mensaje": "Acceso autorizado (Ruta Protegida contra BOLA)",
        "usuario_autenticado": {
            "id": usuario_actual.id,
            "nombre": usuario_actual.nombre,
            "rol": usuario_actual.rol
        },
        "datos": {
            "id_prestamo": prestamo.id_prestamo,
            "id_libro": prestamo.id_libro,
            "usuario_id": prestamo.usuario_id
        }
    }
