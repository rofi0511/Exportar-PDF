from flask import Flask, request, jsonify, send_file, send_from_directory
import pandas as pd
import os
import pdfplumber
from werkzeug.utils import secure_filename
from extractor import extract_movements, extract_bbva
from db import insert_data
from model import predecir_etiqueta
from flask_cors import CORS

app = Flask(__name__, static_folder="build", static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/")
def serve():
    return send_from_directory(app.static_folder, "index.html")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

all_movements = {}

def save_to_file(data_dict, filename, file_type):
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    print(f"Guardando en formato: {file_type}, archivo: {filepath}")

    for sheet_name, df in data_dict.items():
        if "fecha_operacion" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha_operacion"], errors='coerce').dt.strftime("%d/%m/%Y")
        df["retiro"] = df.apply(lambda row: row["monto"] if "retiro" in row["etiqueta"].lower() else 0, axis=1)
        df["deposito"] = df.apply(lambda row: row["monto"] if "deposito" in row["etiqueta"].lower() else 0, axis=1)
        df["referencia"] = df["referencia"].fillna("N/A")
        df["descripcion"] = df["descripcion"].fillna("Sin descripcion")
        df = df.drop(columns=["fecha_operacion", "monto", "banco", "etiqueta"], errors="ignore")

        columnas = ["fecha", "referencia", "deposito", "retiro", "descripcion"]
        if file_type == "excel":
            columnas.append("saldo_operacion")
        df = df[columnas]

        data_dict[sheet_name] = df

    if file_type == "excel":
        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            for sheet_name, df in data_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    elif file_type == "csv":
            df.to_csv(filepath, sep=",", index=False)
    
    elif file_type == "txt":
            df.to_csv(filepath, sep="\t", index=False)
    
    else: 
        print(f"Formato no sportado: {file_type}")
        return None

    return filepath if os.path.exists(filepath) else None

@app.route("/upload", methods=["POST"])
def upload_files():
    global all_movements
    if "files" not in request.files:
        return jsonify({"error": "No files or file type specified"}), 400
    
    files = request.files.getlist("files")
    all_movements.clear()

    base_filename = "movimientos_combinados.xlsx"
    base_filepath = os.path.join(app.config["UPLOAD_FOLDER"], base_filename)
    if os.path.exists(base_filepath):
        os.remove(base_filepath)
        print(f"🗑️ Archivo {base_filename} eliminado para actualizarlo.")

    for file in files:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        
        with pdfplumber.open(filepath) as pdf:
            full_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        
        if "Scotiabank" in full_text:
            bank = "Scotiabank"
            data = extract_movements(full_text, bank)
        elif "BBVA" in full_text:
            bank = "BBVA"
            data = extract_bbva(full_text)
        else:
            return jsonify({"error": f"Banco no reconocido en {filename}"}), 400
        
        if not data.empty:
            data["etiqueta"] = data.apply(lambda row: predecir_etiqueta(row["descripcion"], row["monto"]), axis=1)
            insert_data(data)
            all_movements[filename.replace(".pdf", "")] = data
    
    file_path = save_to_file(all_movements, base_filename, "excel")

    if file_path:
        return jsonify({
            "message": "Files processed successfully", 
            "processed": True,
            "file_path": file_path.replace("\\", "/")
        })

@app.route("/generate", methods=["GET"])
def generate_file():
    file_type = request.args.get("file_type", "excel").lower()
    print(f"🔥 Generando archivo en formato: {file_type}")

    base_filename = "movimientos_combinados.xlsx"
    base_filepath = os.path.join(app.config["UPLOAD_FOLDER"], base_filename)

    if file_type == "excel":
        if os.path.exists(base_filepath):
            return jsonify({
                "message": "File already exists",
                "file": base_filename,
                "file_path": base_filepath.replace("\\", "/")
            })
        else:
            return jsonify({"error": "El archivo base no existe"}), 404
        
    new_extension = "csv" if file_type == "csv"  else "txt"
    new_filename = f"movimientos_combinados.{new_extension}"
    new_filepath = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)

    try:
        df = pd.read_excel(base_filepath, sheet_name=None)
        combined_df = pd.concat(df.values(), ignore_index=True)
        separator = "," if file_type == "csv" else "\t"
        combined_df.to_csv(new_filepath, sep=separator, index=False)

        return jsonify({
            "message": f"File converted to {file_type.upper()}",
            "file_path": new_filepath.replace("\\", "/")
        })
    
    except Exception as e:
        return jsonify({"error": f"No se pudo convertir el archivo: {str(e)}"}), 500

@app.route("/uploads/<filename>", methods=["GET"])
def download_file(filename):
    
    base_dir = r"C:\Users\ASUS-5\OneDrive - MALDONADO VILLASEÑOR CONSULTORES\BS - Contabilidad\Aplicaciones\React\Backend"

    filepath = os.path.join(base_dir, "uploads", filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
