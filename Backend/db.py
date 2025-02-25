import mysql.connector

def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Ro868686",
        database="movimientos_centralizados"
    )

def insert_data(data):
    if data.empty:
        print("⚠️ No hay datos para insertar.")
        return
    conn = connect_db()
    cursor = conn.cursor()
    for _, row in data.iterrows():
        cursor.execute('''
        INSERT INTO movimientos 
        (banco, fecha_operacion, descripcion, referencia, monto, saldo_operacion, etiqueta)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            row.get('banco'), 
            row.get('fecha_operacion'), 
            row.get('descripcion', 'Sin descripción'),
            row.get('referencia', None), 
            float(row.get('monto', 0.0)), 
            float(row.get('saldo_operacion', 0.0)) if row.get('saldo_operacion') is not None else None, 
            row.get('etiqueta', 'Sin etiqueta')
        ))
    conn.commit()
    conn.close()
    print(f"✅ Datos insertados correctamente en la base de datos centralizada.")
