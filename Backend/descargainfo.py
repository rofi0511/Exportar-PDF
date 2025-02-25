import mysql.connector
import pandas as pd
import os

# Configuración de la conexión a MySQL
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Ro868686",
    "database": "movimientos_centralizados" #CAMBIAR LA BASE DE DATOS
}

# Conectar a la base de datos
conn = mysql.connector.connect(**db_config)

# Cargar datos de la tabla `movimientos`
query = "SELECT * FROM movimientos" #CAMBIAR LA TABLA
data = pd.read_sql(query, conn)

# Cerrar la conexión
conn.close()

csv_folder = "CSV"
os.makedirs(csv_folder, exist_ok=True)

# Guardar los datos en un archivo CSV
csv_filename = os.path.join(csv_folder, "movimientos_centralizados_02_25_2.csv") #CAMBIAR EL NOMBRE DEL ARCHIVO

data.to_csv(csv_filename, index=False)

print(f"✅ Datos descargados y guardados en {csv_filename}")
