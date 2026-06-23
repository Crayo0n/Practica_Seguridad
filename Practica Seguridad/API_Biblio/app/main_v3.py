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
    title="API de Biblioteca Digital v3",
    description="Versión 3: API de biblioteca protegida con API Key y JWT",
    version="3.0"
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
        # Convertir el prefijo $2y$ de PHP/MySQL a $2b$ de Python bcrypt
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


# Registrar un nuevo libro
@app.post("/libros", status_code=status.HTTP_201_CREATED)
def registrar_libro(
    libro: schemas.Libro,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
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


# Listar libros
@app.get("/libros", response_model=list[schemas.Libro])
def listar_libros(
    estado: str | None = None,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    query = db.query(models.Libro)
    if estado:
        query = query.filter(models.Libro.estado == estado)
    else:
        query = query.filter(models.Libro.estado == schemas.EstadoLibro.disponible.value)
    return query.all()


# Buscar un libro por su nombre
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


# Registrar un nuevo préstamo
@app.post("/prestamos", status_code=status.HTTP_201_CREATED)
def prestar_libro(
    prestamo: schemas.Prestamo,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    if prestamo.id_prestamo is not None:
        # Verificar si el id_prestamo ya existe
        db_prestamo = (
            db.query(models.Prestamo)
            .filter(models.Prestamo.id_prestamo == prestamo.id_prestamo)
            .first()
        )

        if db_prestamo:
            raise HTTPException(status_code=400, detail="El id_prestamo ya existe")

    # Verificar si el usuario a prestar existe
    usuario_encontrado = (
        db.query(models.Usuario)
        .filter(models.Usuario.id == prestamo.usuario_id)
        .first()
    )

    if not usuario_encontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

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
        id_libro=prestamo.id_libro,
        usuario_id=prestamo.usuario_id
    )
    if prestamo.id_prestamo is not None:
        nuevo_prestamo.id_prestamo = prestamo.id_prestamo

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


# Listar préstamos (Filtrado por rol de usuario para evitar fugas de información)
@app.get("/prestamos", response_model=list[schemas.PrestamoResponse])
def listar_prestamos(
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    if usuario_actual.rol == "admin":
        prestamos = db.query(models.Prestamo).all()
    else:
        prestamos = db.query(models.Prestamo).filter(models.Prestamo.usuario_id == usuario_actual.id).all()

    respuestas = []
    for p in prestamos:
        libro = db.query(models.Libro).filter(models.Libro.id_libro == p.id_libro).first()
        usuario = db.query(models.Usuario).filter(models.Usuario.id == p.usuario_id).first()
        respuestas.append(schemas.PrestamoResponse(
            id_prestamo=p.id_prestamo,
            id_libro=p.id_libro,
            nombre_libro=libro.nombre if libro else "Desconocido",
            usuario_id=p.usuario_id,
            correo_usuario=usuario.email if usuario else "Desconocido"
        ))
    return respuestas


# Marcar un libro como devuelto
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

    libro_encontrado.estado = schemas.EstadoLibro.disponible.value
    db.commit()

    return {"mensaje": "Libro devuelto con éxito. Estado 200 OK."}


# Eliminar el registro de un préstamo
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
        raise HTTPException(status_code=409, detail="Conflicto: El registro de préstamo ya no existe")

    db.delete(prestamo_encontrado)
    db.commit()

    return {"mensaje": "Registro de préstamo eliminado correctamente"}


def obtener_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(14)).decode("utf-8")


# Crear un nuevo usuario (Restringido a Admin en v3)
@app.post("/usuarios", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    usuario: schemas.UsuarioCreate,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    if usuario_actual.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación no permitida: sólo los administradores pueden crear usuarios."
        )
        
    existe = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
    
    nuevo_usuario = models.Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        password=obtener_password_hash(usuario.password),
        rol=usuario.rol
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario
