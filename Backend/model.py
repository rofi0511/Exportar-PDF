import joblib
import pandas as pd
import os

model_path = os.path.join(os.path.dirname(__file__), "modelo_movimientos.pkl")
modelo = joblib.load(model_path)


def predecir_etiqueta(descripcion, monto):
    datos = pd.DataFrame([{ "descripcion": descripcion, "monto": monto }])

    if "descripcion" not in datos.columns or "monto" not in datos.columns:
        print(f"⚠️ Error: Las columnas no existen en datos: {datos.columns}")
        return "Sin etiqueta"

    datos['descripcion'] = datos['descripcion'].astype(str)
    datos['monto'] = datos['monto'].astype(str)

    datos_procesados = datos['descripcion'] + " " + datos['monto']
    return modelo.predict(datos_procesados)[0]

