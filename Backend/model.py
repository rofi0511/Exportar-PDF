import joblib
import pandas as pd
import os

model_path = os.path.join(os.path.dirname(__file__), "modelo_movimientos.pkl")
modelo = joblib.load(model_path)


def predecir_etiqueta(descripcion, monto):
    datos = pd.DataFrame([{ "descripcion": descripcion, "monto": monto }])
    datos_procesados = datos['descripcion'] + " " + datos['monto'].astype(str)
    return modelo.predict(datos_procesados)[0]

