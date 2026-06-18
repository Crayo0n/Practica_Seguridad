from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from datetime import datetime

app = FastAPI(
    title="API de Biblioteca Digital",
    description="Mauricio Rodriguez Molina",
    version="1.0"
)

AÑO_ACTUAL = datetime.now().year

class EstadoLibro(str, Enum):
    disponible = "disponible"
    prestado = "prestado"

# Modelo para el Usuario
class Usuario(BaseModel):
    id: int = Field(..., gt=0, description="Identificador de usuario", example=1)
    nombre: str = Field(..., min_length=2, max_length=50, description="Nombre del usuario")
    correo: EmailStr = Field(..., description="Correo electrónico válido")

# Modelo para el Libro
class Libro(BaseModel):
    id_libro: int = Field(..., gt=0, description="Identificador de libro", example=1)
    nombre: str = Field(..., min_length=2, max_length=100)
    anio_publicacion: int = Field(..., gt=1450, le=AÑO_ACTUAL)
    paginas: int = Field(..., gt=1)
    estado: EstadoLibro = Field(default=EstadoLibro.disponible)

class Prestamo(BaseModel):
    id_prestamo: int = Field(..., gt=0, description="Identificador de Prestamo", example=1)
    id_libro: int 
    nombre_libro: str
    correo_usuario: EmailStr
    
libros_db = []
prestamos_db = []


#Registrar un nuevo libro
@app.post("/libros", status_code=status.HTTP_201_CREATED)
def registrar_libro(libro: Libro):
    for l in libros_db:
        if l.id_libro == libro.id_libro:
            raise HTTPException(status_code=400, detail="El id_libro ya existe")
            
    libros_db.append(libro)
    return {"mensaje": "Libro registrado con éxito", "libro": libro}

#Listar todos los libros Disponibles
@app.get("/libros")
def listar_libros_disponibles():
    disponibles = []
    for libro in libros_db:
        if libro.estado == EstadoLibro.disponible:
            disponibles.append(libro)
    return disponibles

#Buscar un libro por su nombre
@app.get("/libros/{nombre}")
def buscar_libro(nombre: str):
    for libro in libros_db:
        if libro.nombre.lower() == nombre.lower():
            return libro
    
    raise HTTPException(status_code=404, detail="Libro no encontrado en la biblioteca")

#Registrar un nuevo préstamo
@app.post("/prestamos", status_code=status.HTTP_201_CREATED)
def prestar_libro(prestamo: Prestamo):
    for p in prestamos_db:
        if p.id_prestamo == prestamo.id_prestamo:
            raise HTTPException(status_code=400, detail="El id_prestamo ya existe")

    libro_encontrado = None
    for l in libros_db:
        if l.id_libro == prestamo.id_libro:  
            libro_encontrado = l
            break
            
    if not libro_encontrado:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
        
    if libro_encontrado.estado == EstadoLibro.prestado:
        raise HTTPException(status_code=409, detail="Conflicto: El libro ya está prestado")
        
    libro_encontrado.estado = EstadoLibro.prestado
    prestamos_db.append(prestamo)
    return {"mensaje": "Préstamo exitoso", "prestamo": prestamo}

#Marcar un libro como devuelto
@app.put("/libros/{id_libro}/devolver", status_code=status.HTTP_200_OK)
def devolver_libro(id_libro: int):
    libro_encontrado = None
    for l in libros_db:
        if l.id_libro == id_libro:
            libro_encontrado = l
            break
            
    if not libro_encontrado:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
        
    libro_encontrado.estado = EstadoLibro.disponible
    return {"mensaje": "Libro devuelto con éxito. Estado 200 OK."}

#Eliminar el registro de un préstamo
@app.delete("/prestamos/{id_prestamo}")
def eliminar_prestamo(id_prestamo: int): 
    prestamo_encontrado = None
    for p in prestamos_db:
        if p.id_prestamo == id_prestamo:
            prestamo_encontrado = p
            break
            
    if not prestamo_encontrado:
        raise HTTPException(status_code=409, detail="Conflicto: El registro de préstamo ya no existe")
        
    prestamos_db.remove(prestamo_encontrado)
    return {"mensaje": "Registro de préstamo eliminado correctamente"}