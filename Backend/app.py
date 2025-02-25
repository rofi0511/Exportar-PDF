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
    print(f"Guardando: {file_type}")
    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        for sheet_name, df in data_dict.items():
            
            df["retiro"] = df.apply(lambda row: row["monto"] if "retiro" in row["etiqueta"].lower() else 0, axis=1)
            df["deposito"] = df.apply(lambda row: row["monto"] if "deposito" in row["etiqueta"].lower() else 0, axis=1)

            df = df.drop(columns=["etiqueta", "monto"], errors='ignore')

            df.to_excel(writer, sheet_name=sheet_name, index=False)

    #if file_type == "excel":
     #   with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
      #      for sheet_name, df in data_dict.items():
       #         df["retiro"] = df.apply(lambda row: row["monto"] if "retiro" in row["etiqueta"].lower() else 0, axis=1)
        #        df["deposito"] = df.apply(lambda row: row["monto"] if "deposito" in row["etiqueta"].lower() else 0, axis=1)
         #       df = df.drop(columns=["etiqueta", "monto"], errors='ignore')
          #      df.to_excel(writer, sheet_name=sheet_name, index=False)

    #else:
     #   with open(filepath, "w", encoding="utf-8") as f:
      #      f.write("FECHA,REFER,DEPOSITO,RETIRO,DESCRIPCION\n")
       #     for _, df in data_dict.items():
        #        df["FECHA"] = pd.to_datetime(df["fecha_operacion"]).dt.strftime("%d/%m/%Y")
         #       df["DEPOSITO"] = df.apply(lambda row: row["monto"] if "deposito" in row["etiqueta"].lower() else 0, axis=1)
          #      df["RETIRO"] = df.apply(lambda row: row["monto"] if "retiro" in row["etiqueta"].lower() else 0, axis=1)
           ##    df.to_csv(f, sep="," if file_type == "csv" else "\t", index=False, header=False)
                
    return filepath

@app.route("/upload", methods=["POST"])
def upload_files():
    global all_movements
    if "files" not in request.files:
        return jsonify({"error": "No files or file type specified"}), 400
    
    files = request.files.getlist("files")
    all_movements.clear()

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
    
    return jsonify({"message": "Files processed successfully", "processed": True})

@app.route("/generate", methods=["GET"])
def generate_file():
    file_type = request.args.get("file_type", "excel").lower()
    print(f"🔥 Generando archivo en formato: {file_type}")

    if not all_movements:
        return jsonify({"error": "No hay datos procesados"}), 400
    
    file_extension = "xlsx" if file_type == "excel" else file_type
    output_filename = f"movimientos_combinados.{file_extension}"
    file_path = save_to_file(all_movements, output_filename, file_type)

    if os.path.exists(file_path):  # ✅ Verificamos que el archivo se haya creado
        normalized_path = os.path.normpath(file_path).replace("\\", "/")
        return jsonify({"message": "File generated", "file": output_filename, "file_path": normalized_path})
    else:
        return jsonify({"error": "No se pudo generar el archivo"}), 500

@app.route("/uploads/<filename>", methods=["GET"])
def download_file(filename):
    
    base_dir = r"C:\Users\ASUS-5\OneDrive - MALDONADO VILLASEÑOR CONSULTORES\BS - Contabilidad\Aplicaciones\React"

    filepath = os.path.join(base_dir, "uploads", filename)
    #filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
