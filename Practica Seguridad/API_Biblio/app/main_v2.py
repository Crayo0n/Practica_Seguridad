import os
from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models
from app import schemas

app = FastAPI(
    title="API de Biblioteca Digital v2",
    description="Versión 2: API de biblioteca protegida con API Key",
    version="2.0"
)

API_KEY_VALIDA = os.getenv("API_KEY", "BIBLIO123")


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


# Registrar un nuevo libro
@app.post("/libros", status_code=status.HTTP_201_CREATED)
def registrar_libro(
    libro: schemas.Libro,
    api_key_valida: bool = Depends(validar_api_key),
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

    # Verificar si el usuario existe
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


# Listar todos los préstamos
@app.get("/prestamos", response_model=list[schemas.PrestamoResponse])
def listar_prestamos(
    api_key_valida: bool = Depends(validar_api_key),
    db: Session = Depends(get_db)
):
    prestamos = db.query(models.Prestamo).all()
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


import bcrypt

def obtener_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(14)).decode("utf-8")


# Crear un nuevo usuario (Protegido por API Key en v2)
@app.post("/usuarios", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    usuario: schemas.UsuarioCreate,
    api_key_valida: bool = Depends(validar_api_key),
    db: Session = Depends(get_db)
):
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
