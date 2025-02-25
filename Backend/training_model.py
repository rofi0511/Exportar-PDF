import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
import joblib
import os

# Seleccionar los archivos CSV a cargar
csv_folder = "CSV"

csv_files = [
    os.path.join(csv_folder, "movimientos_centralizados_02_25.csv")
]

data_frames = [pd.read_csv(file) for file in csv_files]
data = pd.concat(data_frames, ignore_index=True)

# Rellenar valores nulos
data['descripcion'] = data['descripcion'].fillna('')
data['referencia'] = data['referencia'].fillna('N/A').astype(str)
data['saldo_operacion'] = data['saldo_operacion'].fillna(0.0).astype(float)

# Seleccionar características relevantes
X = data['descripcion'] + " " + data['monto'].astype(str)  # Combinar descripción con monto
y = data['etiqueta']  # La etiqueta a predecir

# Dividir datos en entrenamiento y prueba
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Crear un modelo que use NLP (TF-IDF) + Random Forest
model = make_pipeline(TfidfVectorizer(max_features=500), RandomForestClassifier(random_state=42))

# Entrenar el modelo
model.fit(X_train, y_train)

# Evaluar el modelo
accuracy = model.score(X_test, y_test)

# Leer la precisión anterior si existe
accuracy_file = "accuracy_history.txt"
previous_accuracy = None
if os.path.exists(accuracy_file):
    with open(accuracy_file, "r") as f:
        previous_accuracy = float(f.read().strip())

# Mostrar comparación con precisión anterior
if previous_accuracy is not None:
    change = accuracy * 100 - previous_accuracy
    status = "🔼 Mejoró" if change > 0 else "🔽 Empeoró"
    print(f"🎯 Precisión del modelo: {accuracy * 100:.2f}% ({status} {abs(change):.2f}%)")
else:
    print(f"🎯 Precisión del modelo: {accuracy * 100:.2f}% (Primera ejecución)")

# Guardar la nueva precisión
with open(accuracy_file, "w") as f:
    f.write(f"{accuracy * 100:.2f}")

# Guardar el modelo entrenado
joblib.dump(model, 'modelo_movimientos.pkl')
print("✅ Modelo guardado como 'modelo_movimientos.pkl'")
