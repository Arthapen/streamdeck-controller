from flask import Flask, send_from_directory
from pathlib import Path

# Rutas basadas en la ubicación de este archivo
COMPANION_DIR = Path(__file__).resolve().parent
BASE_DIR = COMPANION_DIR.parent
CLIENT_DIR = BASE_DIR / "web-client"

app = Flask(__name__)

# Raíz -> client.html
@app.route("/")
def root():
    return send_from_directory(CLIENT_DIR, "client.html")

# Servir cualquier archivo dentro de web-client (css/js/img, etc.)
@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(CLIENT_DIR, path)

if __name__ == "__main__":
    # 0.0.0.0 para que también puedas abrirlo desde el celu vía IP de la PC
    app.run(host="0.0.0.0", port=8080)
