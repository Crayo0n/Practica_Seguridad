import os

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, session

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "FRONTEND_SECRET_KEY",
    "clave_secreta_frontend_laboratorio"
)

API_KEY = os.getenv("API_KEY", "ABC123")

API_URLS = {
    "v1": "http://api_v1:8000",
    "v2": "http://api_v2:8000",
    "v3": "http://api_v3:8000",
    "v4": "http://api_v4:8000",
    "v5": "http://api_v5:8000"
}


def obtener_api_actual():
    return session.get("api_version", "v1")


def obtener_base_url():
    api_version = obtener_api_actual()
    return API_URLS[api_version]


def requiere_api_key(api_version):
    return api_version in ["v2", "v3", "v4", "v5"]


def requiere_jwt(api_version):
    return api_version in ["v3", "v4", "v5"]


def construir_headers():
    api_version = obtener_api_actual()
    headers = {}

    if requiere_api_key(api_version):
        headers["x-api-key"] = API_KEY

    token = session.get("access_token")

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
                "error": "No se pudo conectar con la API",
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
            session.pop("access_token", None)
            session.pop("usuario", None)

            resultado = {
                "ok": True,
                "status_code": None,
                "url": None,
                "data": {
                    "mensaje": f"API activa cambiada a {nueva_version.upper()}",
                    "nota": "Se limpia el token anterior para evitar mezclar sesiones entre versiones."
                }
            }

        elif accion == "login":
            email = request.form.get("email")
            password = request.form.get("password")

            api_version = obtener_api_actual()

            if not requiere_jwt(api_version):
                resultado = {
                    "ok": False,
                    "status_code": None,
                    "url": None,
                    "data": {
                        "error": "Esta versión no usa login",
                        "mensaje": "V1 no tiene seguridad y V2 solo usa API Key. Usa V3 o V4 para login con JWT."
                    }
                }
            else:
                resultado = llamar_api(
                    "POST",
                    "/login",
                    json={
                        "email": email,
                        "password": password
                    }
                )

                if resultado["ok"]:
                    token = resultado["data"].get("access_token")
                    session["access_token"] = token

                    perfil = llamar_api("GET", "/api/perfil")

                    if perfil["ok"]:
                        session["usuario"] = perfil["data"]

        elif accion == "logout":
            session.pop("access_token", None)
            session.pop("usuario", None)

            resultado = {
                "ok": True,
                "status_code": None,
                "url": None,
                "data": {
                    "mensaje": "Sesión cerrada en el frontend"
                }
            }

        elif accion == "perfil":
            resultado = llamar_api("GET", "/api/perfil")

        elif accion == "alumnos":
            resultado = llamar_api("GET", "/api/alumnos")

        elif accion == "alumno_id":
            id_alumno = request.form.get("id_alumno", "1")
            resultado = llamar_api("GET", f"/api/alumnos/{id_alumno}")

        elif accion == "maestros":
            resultado = llamar_api("GET", "/api/maestros")

        elif accion == "maestro_id":
            id_maestro = request.form.get("id_maestro", "1")
            resultado = llamar_api("GET", f"/api/maestros/{id_maestro}")

        elif accion == "bola_vulnerable":
            id_alumno = request.form.get("id_alumno_vulnerable", "2")
            resultado = llamar_api(
                "GET",
                f"/api/vulnerable/alumnos/{id_alumno}"
            )

    api_version = obtener_api_actual()

    return render_template(
        "index.html",
        api_version=api_version,
        api_url=API_URLS[api_version],
        requiere_api_key=requiere_api_key(api_version),
        requiere_jwt=requiere_jwt(api_version),
        usuario=session.get("usuario"),
        token=session.get("access_token"),
        resultado=resultado
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=9000,
        debug=True
    )