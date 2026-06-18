import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

from database import get_db
from models import Alumno, Maestro, Usuario

load_dotenv()

app = FastAPI(
    title="API Escuela v5",
    description="Version 5: API Key + JWT + roles + BOLA/IDOR + rate limiting",
    version="5.0.0"
)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="memory://"
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "Demasiadas solicitudes",
            "mensaje": "Has excedido el limite permitido. Intenta mas tarde.",
            "detalle": str(exc.detail)
        }
    )

API_KEY_VALIDA = os.getenv("API_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


def validar_api_key(
    x_api_key: str | None = Header(default=None, alias="x-api-key")
):
    if x_api_key != API_KEY_VALIDA:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "No autorizado",
                "mensaje": "API Key invalida o no enviada"
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
        "alumno_id": usuario.alumno_id,
        "maestro_id": usuario.maestro_id,
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
                    "error": "Token invalido",
                    "mensaje": "El token no contiene identidad de usuario"
                }
            )

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Token invalido",
                "mensaje": "El token es invalido o expiro"
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


def requiere_rol(*roles_permitidos):
    def dependencia(usuario_actual: Usuario = Depends(obtener_usuario_actual)):
        if usuario_actual.rol not in roles_permitidos:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Acceso denegado",
                    "mensaje": "No tienes el rol necesario para esta accion"
                }
            )

        return usuario_actual

    return dependencia


@app.get("/")
def inicio():
    return {
        "mensaje": "API de escuela con API Key, JWT, roles y proteccion BOLA/IDOR - v4",
        "usuarios_prueba": [
            {
                "email": "isabel@email.com",
                "password": "123456",
                "rol": "alumno"
            },
            {
                "email": "samantha@email.com",
                "password": "123456",
                "rol": "alumno"
            },
            {
                "email": "luis@email.com",
                "password": "admin123",
                "rol": "maestro"
            },
            {
                "email": "admin@escuela.com",
                "password": "admin123",
                "rol": "admin"
            }
        ],
        "endpoints": [
            "POST /login",
            "GET /api/perfil",
            "GET /api/vulnerable/alumnos/{id_alumno}",
            "GET /api/alumnos",
            "GET /api/alumnos/{id_alumno}",
            "GET /api/maestros",
            "GET /api/maestros/{id_maestro}"
        ]
    }


@app.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
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
                "error": "Credenciales invalidas"
            }
        )

    if not verificar_password(datos.password, usuario.password):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Credenciales invalidas"
            }
        )

    token = crear_token(usuario)

    return {
        "mensaje": "Login exitoso",
        "access_token": token,
        "token_type": "bearer"
    }


@app.get("/api/perfil")
@limiter.limit("30/minute")
def perfil(
    request: Request,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: Usuario = Depends(obtener_usuario_actual)
):
    return {
        "usuario_id": usuario_actual.id,
        "nombre": usuario_actual.nombre,
        "email": usuario_actual.email,
        "rol": usuario_actual.rol,
        "alumno_id": usuario_actual.alumno_id,
        "maestro_id": usuario_actual.maestro_id
    }


# ---------------------------------------------------------
# RUTA VULNERABLE PARA DEMOSTRAR BOLA/IDOR
# ---------------------------------------------------------

@app.get("/api/vulnerable/alumnos/{id_alumno}")
@limiter.limit("10/minute")
def obtener_alumno_vulnerable(
    request: Request,
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

    return {
        "advertencia": "Esta ruta es vulnerable a BOLA/IDOR",
        "explicacion": "Valida API Key y JWT, pero no valida si el alumno solicitado pertenece al usuario autenticado.",
        "usuario_autenticado": {
            "id": usuario_actual.id,
            "nombre": usuario_actual.nombre,
            "rol": usuario_actual.rol,
            "alumno_id": usuario_actual.alumno_id
        },
        "datos": alumno
    }


# ---------------------------------------------------------
# RUTAS PROTEGIDAS CON ROLES Y VALIDACIoN A NIVEL DE OBJETO
# ---------------------------------------------------------

@app.get("/api/alumnos")
@limiter.limit("20/minute")
def obtener_alumnos(
    request: Request,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: Usuario = Depends(requiere_rol("maestro", "admin")),
    db: Session = Depends(get_db)
):
    return db.query(Alumno).all()


@app.get("/api/alumnos/{id_alumno}")
@limiter.limit("30/minute")
def obtener_alumno_por_id(
    request: Request,
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

    if usuario_actual.rol == "admin":
        return alumno

    if usuario_actual.rol == "maestro":
        return alumno

    if (
        usuario_actual.rol == "alumno"
        and usuario_actual.alumno_id == id_alumno
    ):
        return alumno

    raise HTTPException(
        status_code=403,
        detail={
            "error": "Acceso denegado",
            "mensaje": "No puedes consultar datos de otro alumno"
        }
    )


@app.get("/api/maestros")
@limiter.limit("20/minute")
def obtener_maestros(
    request: Request,
    api_key_valida: bool = Depends(validar_api_key),
    usuario_actual: Usuario = Depends(requiere_rol("admin")),
    db: Session = Depends(get_db)
):
    return db.query(Maestro).all()


@app.get("/api/maestros/{id_maestro}")
@limiter.limit("30/minute")
def obtener_maestro_por_id(
    request: Request,
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

    if usuario_actual.rol == "admin":
        return maestro

    if (
        usuario_actual.rol == "maestro"
        and usuario_actual.maestro_id == id_maestro
    ):
        return maestro

    raise HTTPException(
        status_code=403,
        detail={
            "error": "Acceso denegado",
            "mensaje": "No puedes consultar datos de este maestro"
        }
    )