import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Alumno, Maestro, Usuario

load_dotenv()

app = FastAPI(
    title="API Escuela v3",
    description="Versión 3: API Key + JWT usando MySQL",
    version="3.0.0"
)

API_KEY_VALIDA = os.getenv("API_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


def validar_api_key(x_api_key: str | None = Header(default=None, alias="x-api-key")):
    if x_api_key != API_KEY_VALIDA:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "No autorizado",
                "mensaje": "API Key inválida o no enviada"
            }
        )

    return True


def verificar_password(password_plano: str, password_hash: str):
    password_hash = password_hash.replace("$2y$", "$2b$")
    return bcrypt.checkpw(
        password_plano.encode("utf-8"),
        password_hash.encode("utf-8")
    )


def crear_token(usuario: Usuario):
    expiracion = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(usuario.id),
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "exp": expiracion
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return token


def obtener_usuario_actual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "No autorizado",
                "mensaje": "Token JWT no enviado"
            }
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        usuario_id = payload.get("sub")

        if usuario_id is None:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Token inválido",
                    "mensaje": "El token no contiene identidad de usuario"
                }
            )

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Token inválido",
                "mensaje": "El token es inválido o expiró"
            }
        )

    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == int(usuario_id))
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Usuario no encontrado"
            }
        )

    return usuario

@app.post("/login")
def login(
    datos: LoginRequest,
    api_key_valida: bool = Depends(validar_api_key),
    db: Session = Depends(get_db)
):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == datos.email)
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Credenciales inválidas"
            }
        )

    if not verificar_password(datos.password, usuario.password):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Credenciales inválidas"
            }
        )

    token = crear_token(usuario)

    return {
        "mensaje": "Login exitoso",
        "access_token": token,
        "token_type": "bearer"
    }


@app.get("/api/perfil")
def perfil(
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: Usuario = Depends(obtener_usuario_actual)
):
    return {
        "id": usuario_actual.id,
        "nombre": usuario_actual.nombre,
        "email": usuario_actual.email,
        "rol": usuario_actual.rol,
        "alumno_id": usuario_actual.alumno_id,
        "maestro_id": usuario_actual.maestro_id
    }


@app.get("/api/alumnos")
def obtener_alumnos(
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    return db.query(Alumno).all()


@app.get("/api/alumnos/{id_alumno}")
def obtener_alumno_por_id(
    id_alumno: int,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    alumno = (
        db.query(Alumno)
        .filter(Alumno.id == id_alumno)
        .first()
    )

    if not alumno:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Alumno no encontrado"
            }
        )

    return alumno


@app.get("/api/maestros")
def obtener_maestros(
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    return db.query(Maestro).all()


@app.get("/api/maestros/{id_maestro}")
def obtener_maestro_por_id(
    id_maestro: int,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    maestro = (
        db.query(Maestro)
        .filter(Maestro.id == id_maestro)
        .first()
    )

    if not maestro:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Maestro no encontrado"
            }
        )

    return maestro