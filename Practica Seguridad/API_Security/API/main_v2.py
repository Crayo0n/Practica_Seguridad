import os

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Alumno, Maestro

app = FastAPI(
    title="API v2",
    description="Versión 2: API protegida con API Key usando MySQL",
    version="2.0.0"
)

API_KEY_VALIDA = os.getenv("API_KEY")


def validar_api_key(x_api_key: str | None = Header(default=None)):
    if x_api_key != API_KEY_VALIDA:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "No autorizado",
                "mensaje": "API Key inválida o no enviada"
            }
        )

    return True

@app.get("/api/alumnos")
def obtener_alumnos(
    api_key_valida: bool = Depends(validar_api_key),
    db: Session = Depends(get_db)
):
    return db.query(Alumno).all()


@app.get("/api/alumnos/{id_alumno}")
def obtener_alumno_por_id(
    id_alumno: int,
    api_key_valida: bool = Depends(validar_api_key),
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
    db: Session = Depends(get_db)
):
    return db.query(Maestro).all()


@app.get("/api/maestros/{id_maestro}")
def obtener_maestro_por_id(
    id_maestro: int,
    api_key_valida: bool = Depends(validar_api_key),
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