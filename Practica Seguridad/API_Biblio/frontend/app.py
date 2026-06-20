import os
import requests
from flask import Flask, render_template, request, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FRONTEND_SECRET_KEY", "clave_secreta_frontend_biblioteca")

API_KEY = os.getenv("API_KEY", "BIBLIO123")

API_URLS = {
    "v1": "http://api_v1:5005",
    "v2": "http://api_v2:5005",
    "v3": "http://api_v3:5005",
    "v4": "http://api_v4:5005",
    "v5": "http://api_v5:5005"
}


def obtener_api_actual():
    return session.get("api_version", "v1")


def obtener_base_url():
    api_version = obtener_api_actual()
    return API_URLS[api_version]


def requiere_api_key(api_version):
    # v2, v3, v4 y v5 requieren API Key
    return api_version in ["v2", "v3", "v4", "v5"]


def requiere_jwt(api_version):
    # v3, v4 y v5 requieren JWT
    return api_version in ["v3", "v4", "v5"]


def construir_headers():
    api_version = obtener_api_actual()
    headers = {}

    if requiere_api_key(api_version):
        headers["x-api-key"] = API_KEY

    if requiere_jwt(api_version):
        token = session.get("jwt_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

    return headers


def llamar_api(method, endpoint, json=None):
    base_url = obtener_base_url()
    url = f"{base_url}{endpoint}"

    try:
        respuesta = requests.request(
            method=method,
            url=url,
            headers=construir_headers(),
            json=json,
            timeout=5
        )

        try:
            contenido = respuesta.json()
        except ValueError:
            contenido = respuesta.text

        return {
            "ok": respuesta.ok,
            "status_code": respuesta.status_code,
            "url": url,
            "data": contenido
        }

    except requests.RequestException as error:
        return {
            "ok": False,
            "status_code": None,
            "url": url,
            "data": {
                "error": "No se pudo conectar con la API de Biblioteca",
                "detalle": str(error)
            }
        }


@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None

    if request.method == "POST":
        accion = request.form.get("accion")

        if accion == "cambiar_api":
            nueva_version = request.form.get("api_version", "v1")
            session["api_version"] = nueva_version
            # Limpiar datos de autenticación al cambiar de versión
            session.pop("jwt_token", None)
            session.pop("usuario_perfil", None)
            resultado = {
                "ok": True,
                "status_code": None,
                "url": None,
                "data": {
                    "mensaje": f"API activa cambiada a {nueva_version.upper()}"
                }
            }

        elif accion == "login":
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            resultado = llamar_api(
                "POST",
                "/login",
                json={
                    "email": email,
                    "password": password
                }
            )
            if resultado.get("ok"):
                session["jwt_token"] = resultado["data"].get("access_token")
                session["usuario_perfil"] = resultado["data"].get("usuario")

        elif accion == "logout":
            session.pop("jwt_token", None)
            session.pop("usuario_perfil", None)
            resultado = {
                "ok": True,
                "status_code": None,
                "url": None,
                "data": {
                    "mensaje": "Sesión cerrada correctamente"
                }
            }

        elif accion == "perfil":
            resultado = llamar_api("GET", "/api/perfil")
            if resultado.get("ok"):
                session["usuario_perfil"] = resultado["data"]

        elif accion == "libros":
            resultado = llamar_api("GET", "/libros")

        elif accion == "buscar_libro":
            nombre = request.form.get("nombre_libro", "")
            resultado = llamar_api("GET", f"/libros/{nombre}")

        elif accion == "crear_prestamo":
            try:
                id_prestamo = int(request.form.get("id_prestamo", "1"))
                id_libro = int(request.form.get("id_libro", "1"))
                usuario_id = int(request.form.get("usuario_id", "1"))
                resultado = llamar_api(
                    "POST",
                    "/prestamos",
                    json={
                        "id_prestamo": id_prestamo,
                        "id_libro": id_libro,
                        "usuario_id": usuario_id
                    }
                )
            except ValueError:
                resultado = {
                    "ok": False,
                    "status_code": 400,
                    "url": None,
                    "data": {"error": "Los IDs de préstamo, libro y usuario deben ser números enteros."}
                }

        elif accion == "devolver_libro":
            try:
                id_libro = int(request.form.get("id_libro_devolver", "1"))
                resultado = llamar_api("PUT", f"/libros/{id_libro}/devolver")
            except ValueError:
                resultado = {
                    "ok": False,
                    "status_code": 400,
                    "url": None,
                    "data": {"error": "El ID del libro debe ser un número entero."}
                }

        elif accion == "eliminar_prestamo":
            try:
                id_prestamo = int(request.form.get("id_prestamo_eliminar", "1"))
                resultado = llamar_api("DELETE", f"/prestamos/{id_prestamo}")
            except ValueError:
                resultado = {
                    "ok": False,
                    "status_code": 400,
                    "url": None,
                    "data": {"error": "El ID de préstamo debe ser un número entero."}
                }

        elif accion == "ver_prestamo_vulnerable":
            try:
                id_prestamo = int(request.form.get("id_prestamo_ver", "1"))
                resultado = llamar_api("GET", f"/api/vulnerable/prestamos/{id_prestamo}")
            except ValueError:
                resultado = {
                    "ok": False,
                    "status_code": 400,
                    "url": None,
                    "data": {"error": "El ID de préstamo debe ser un número entero."}
                }

        elif accion == "ver_prestamo_seguro":
            try:
                id_prestamo = int(request.form.get("id_prestamo_ver", "1"))
                resultado = llamar_api("GET", f"/api/prestamos/{id_prestamo}")
            except ValueError:
                resultado = {
                    "ok": False,
                    "status_code": 400,
                    "url": None,
                    "data": {"error": "El ID de préstamo debe ser un número entero."}
                }

    api_version = obtener_api_actual()

    return render_template(
        "index.html",
        api_version=api_version,
        api_url=API_URLS[api_version],
        requiere_api_key=requiere_api_key(api_version),
        requiere_jwt=requiere_jwt(api_version),
        jwt_token=session.get("jwt_token"),
        usuario_perfil=session.get("usuario_perfil"),
        resultado=resultado
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=9000,
        debug=True
    )
