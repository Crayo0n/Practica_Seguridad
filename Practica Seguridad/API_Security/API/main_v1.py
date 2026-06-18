from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Alumno, Maestro

app = FastAPI(
    title="API v1",
    description="Versión 1: API básica sin seguridad usando MySQL",
    version="1.0.0"
)

@app.get("/api/alumnos")
def obtener_alumnos(db: Session = Depends(get_db)):
    return db.query(Alumno).all()


@app.get("/api/alumnos/{id_alumno}")
def obtener_alumno_por_id(
    id_alumno: int,
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
            detail="Alumno no encontrado"
        )

    return alumno


@app.get("/api/maestros")
def obtener_maestros(db: Session = Depends(get_db)):
    return db.query(Maestro).all()


@app.get("/api/maestros/{id_maestro}")
def obtener_maestro_por_id(
    id_maestro: int,
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
            detail="Maestro no encontrado"
        )

    return maestro