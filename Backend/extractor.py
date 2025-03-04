import pandas as pd
import re
from datetime import datetime
from model import predecir_etiqueta

def format_date(date_str):
    try:
        month_map = {
            "ENE": "Jan", "FEB": "Feb", "MAR": "Mar", "ABR": "Apr",
            "MAY": "May", "JUN": "Jun", "JUL": "Jul", "AGO": "Aug",
            "SEP": "Sep", "OCT": "Oct", "NOV": "Nov", "DIC": "Dec"
        }
        
        if "/" in date_str:
            day, month = date_str.split("/")  # Formato BBVA "05/FEB"
        else:
            parts = date_str.split()
            if len(parts) < 2:
                raise ValueError("Formato de fecha incorrecto")
            day, month = parts  # Formato Scotiabank "05 FEB"
        
        month = month.upper()
        if month not in month_map:
            raise ValueError(f"Mes desconocido: {month}")
        
        formatted_date = f"{day} {month_map[month]} 2024"
        return datetime.strptime(formatted_date, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError as e:
        print(f"⚠️ Error al convertir fecha: {date_str} - {e}")
        return "2024-01-01"

def extract_relevant_text(text, start_marker, end_marker):
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        return text  
    
    return text[start_idx + len(start_marker):end_idx].strip()

def extract_movements(text, bank):
    start_marker = "Detalledetusmovimientos" if bank == "Scotiabank" else "Detalle de Movimientos Realizados"
    end_marker = "LASTASASDEINTERESESTANEXPRESADASENTERMINOSANUALESSIMPLES." if bank == "Scotiabank" else "Total de Movimientos"
    
    text = extract_relevant_text(text, start_marker, end_marker)
    lines = text.split('\n')
    movements = []
    buffer = ""
    date_pattern = re.compile(r'\b(\d{2})[ /](ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\b')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.search(r'\$\d{1,3}(?:,\d{3})*\.\d{2}', line):
            if buffer:
                line = buffer + " " + line
                buffer = ""
        else:
            buffer += line + " "
            continue

        parts = line.split()
        if len(parts) < 6:
            print("⚠️ Línea descartada por tener menos de 5 elementos")
            continue

        date_match = date_pattern.search(line)

        if not date_match:
            print("⚠️ No se encontró fecha en la línea")
            continue    

        fecha = format_date(date_match.group())
        #remaining_line = line.replace(date_match.group(0), "").strip()
        remaining_parts = line.replace(date_match.group(0), "").strip().split()
       
        if len(remaining_parts) < 3:
            continue
        descripcion = " ".join(remaining_parts[:-3])
        referencia = remaining_parts[-3] if bank == "Scotiabank" else None
        
        try:
            monto = float(remaining_parts[-2].replace(',', '').replace('$', ''))
            saldo = float(remaining_parts[-1].replace(',', '').replace('$', '')) if bank == "Scotiabank" else None
        except ValueError:
            print(f"⚠️ Error al convertir monto/saldo en la línea: {line}")
            continue
        
        etiqueta_predicha = predecir_etiqueta(descripcion, monto)
        
        movements.append({
            "banco": bank,
            "fecha_operacion": fecha,
            "descripcion": descripcion,
            "referencia": referencia,
            "monto": monto,
            "saldo_operacion": saldo,
            "etiqueta": etiqueta_predicha
        })
    return pd.DataFrame(movements)

def extract_bbva(text):
    print("BANCOMER")
    text = extract_relevant_text(text, "Detalle de Movimientos Realizados", "Total de Movimientos")
    lines = text.split('\n')
    movements = []
    date_pattern = re.compile(r'\d{2}/\w{3}')

    for line in lines:
        if date_pattern.match(line.strip()):
            parts = line.split()
            if len(parts) > 2:
                oper_date = parts[0]
                amounts = [part for part in parts if re.match(r'\d{1,3}(?:,\d{3})*\.\d{2}', part)]
                description_end_index = parts.index(amounts[0]) if amounts else len(parts)
                description = " ".join(parts[2:description_end_index])

                cargo = "0"
                abono = "0"

                if any(keyword in description.lower() for keyword in ["abono", "depósito", "traspaso", "recibidos"]):
                    abono = amounts[0]
                else:
                    cargo = amounts[0]

                etiqueta_predicha = predecir_etiqueta(description, amounts)

                fecha = format_date(oper_date)

                movements.append({
                    "banco": "BBVA",
                    "fecha_operacion": fecha,
                    "descripcion": description,
                    "referencia": None,
                    "monto": float(abono.replace(',', '').replace('$', '')) if abono != "0" else float(cargo.replace(',', '').replace('$', '')),
                    "saldo_operacion": None,
                    "etiqueta": etiqueta_predicha
                })
    return pd.DataFrame(movements)

def clean_banamex_text(text):
    
    lines = text.split("\n")
    cleaned_lines = []

    problematic_pattern = re.compile(r"000180\.B07CHDA\d{3}\.OD\.\d{4}\.\d{2}")

    for line in lines:
        line = line.strip()

        if problematic_pattern.search(line):
            continue

        cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    return text

def extract_banamex(text):

    text_1 = extract_relevant_text(text,"DETALLE DE OPERACIONES","SALDO MINIMO REQUERIDO")
    print(f"📄 Texto extraído antes de limpiar:\n{text_1[:1000]}")  # Solo los primeros 1000 caracteres para revisar

    lines = text.split('\n')
    movements = []
    buffer = ""

    print("Banamex en extractor.py")

    date_pattern = re.compile(r'\b\d{2} \b(JUL|ENE|FEB|MAR|ABR|MAY|JUN|AGO|SEP|OCT|NOV|DIC)\b', re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        date_match = date_pattern.search(line)
        amount_matches = re.findall(r'\d{1,3}(?:,\d{3})*\.\d{2}', line)

        if date_match:
            if buffer:
                movements.append(process_banamex_line(buffer))
                buffer = ""

        buffer += " " + line

    if buffer:
        movements.append(process_banamex_line(buffer))

    df = pd.DataFrame([m for m in movements if m])

    print(f"📊 Movimientos extraídos de Banamex: {len(df)} registros")
    print(df.head())  # Muestra las primeras filas del DataFrame para verificar estructura

    return df

def process_banamex_line(line):

    date_pattern = re.compile(r'\b\d{2} \b(JUL|ENE|FEB|MAR|ABR|MAY|JUN|AGO|SEP|OCT|NOV|DIC)\b', re.IGNORECASE)
    amount_pattern = re.compile(r'\d{1,3}(?:,\d{3})*\.\d{2}')

    date_match = date_pattern.search(line)
    if not date_match:
        return None
    
    fecha = format_date(date_match.group())
    amount_matches = amount_pattern.findall(line)

    if not amount_matches:
        return None
    
    if len(amount_matches) == 1:
        monto = float(amount_matches[0].replace(",", ""))
        saldo = None
    elif len(amount_matches) == 2:
        monto = float(amount_matches[0].replace(",", ""))
        saldo = float(amount_matches[1].replace(",", ""))
    elif len(amount_matches) == 3:
        monto = float(amount_matches[1].replace(",", ""))
        saldo = float(amount_matches[2].replace(",", ""))
    else:
        print(f"⚠️ Demasiados montos detectados en la línea: {line}")
        return None

    descripcion = line.replace(date_match.group(), "").strip()
    for amt in amount_matches:
        descripcion = descripcion.replace(amt, "").strip()

    etiqueta_predicha = predecir_etiqueta(descripcion, monto)

    movimiento = {
        "banco": "Banamex",
        "fecha_operacion": fecha,
        "descripcion": descripcion,
        "referencia": None,
        "monto": monto,
        "saldo_operacion": saldo,
        "etiqueta": etiqueta_predicha
    }

    print(f"📝 Movimiento procesado: {movimiento}")

    return movimiento

def extract_banregio(text):
    start_marker = "DIA CONCEPTO CARGOS ABONOS SALDO"
    text = text[text.find(start_marker) + len(start_marker):].strip()
    lines = text.split('\n')
    movements = []

    date_pattern = re.compile(r'\b\d{1,2}\b')
    amount_pattern = re.compile(r'\d{1,3}(?:,\d{3})*\.\d{2}')

    for line in lines:
        line = line.strip()
        if not line or not date_pattern.match(line.split()[0]):
            continue

        parts = line.split()
        day = parts[0]

        amounts = [p for p in parts if amount_pattern.match(p)]
        if len(amounts) > 2:
            print(f"⚠️ Línea ignorada por falta de montos: {line}")
            continue
        
        try:
            saldo = float(amounts[-1].replace(',', ''))
            monto = float(amounts[-2].replace(',', ''))
        except IndexError:
            print(f"⚠️ Error procesando montos en línea: {line}")
            continue

        concepto = " ".join(parts[1:-len(amounts)])

        fecha = format_date(day) if day.isdigit() else "2024-01-01"
        etiqueta_predicha = predecir_etiqueta(concepto, monto)

        movements.append({
            "banco": "Banregio",
            "fecha_operacion": fecha,
            "descripcion": concepto,
            "referencia": None,
            "monto": monto,
            "saldo_operacion": saldo,
            "etiqueta": etiqueta_predicha
        })
    
    return pd.DataFrame(movements)

def extract_azteca(text):
    lines = text.split('\n')
    movements = []

    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    amount_pattern = re.compile(r'\d{1,3}(?:,\d{3})*\.\d{2}')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 7:
            continue

        fecha_operacion = parts[0]
        if not date_pattern.match(fecha_operacion):
            continue

        concepto = " ".join(parts[4:-3])

        cargos = parts[-3]
        abonos = parts[-2]
        saldo = parts[-1]

        try:
            monto = float(abonos.replace(',', '')) if abonos != '0.00' else float(cargos.replace(',', ''))
            saldo = float(saldo.replace(',', ''))
        except ValueError:
            continue

        etiqueta_predicha = predecir_etiqueta(concepto, monto)

        movements.append({
            "banco": "Banco Azteca",
            "fecha_operacion": fecha_operacion,
            "descripcion": concepto,
            "referencia": None,
            "monto": monto,
            "saldo_operacion": saldo,
            "etiqueta": etiqueta_predicha
        })

    return pd.DataFrame(movements)

def extract_inbursa(text):
    start_marker = "DETALLE DE MOVIMIENTOS"
    end_marker = "RESUMEN DEL CFDI"

    text = extract_relevant_text(text, start_marker, end_marker)

    lines = text.split('\n')
    movements = []
    date_pattern = re.compile(r'\b\b(JUL|ENE|FEB|MAR|ABR|MAY|JUN|AGO|SEP|OCT|NOV|DIC)\s+\d{2}\b', re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line or not date_pattern.search(line):
            continue

        parts = line.split()
        if len(parts) < 4:
            continue

        try:
            fecha = format_date(parts[0] + " " + parts[1])
            referencia = parts[2] if parts[2].isdigit() else None
            descripcion_start = 3 if referencia else 2
            descripcion = " ".join(parts[descripcion_start:-2])
            monto = float(parts[-2].replace(',', '').replace('$', ''))
            saldo = float(parts[-1].replace(',', '').replace('$', ''))

        except ValueError:
            print(f"⚠️ Error al procesar la línea: {line}")
            continue

        eitqueta_predicha = predecir_etiqueta(descripcion, monto)

        movements.append({
            "banco": "Inbursa",
            "fecha_operacion": fecha,
            "descripcion": descripcion,
            "referencia": referencia,
            "monto": monto,
            "saldo_operacion": saldo,
            "etiqueta": eitqueta_predicha
        })
    return pd.DataFrame(movements)

def format_date_santander(date_str):
    try:
        return datetime.strptime(date_str, "%d-%b-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return "2024.01.01"

def extract_santander(text):
    # Extraer todas las páginas correctamente
    sections = []
    start_marker = "Detalle de movimientos cuenta de cheques."
    end_marker = "SALDO FINAL DEL PERIODO"
    
    pages = text.split("\nP-P")  # Separar por páginas
    
    for page in pages:
        start_idx = page.find(start_marker)
        if start_idx != -1:
            extracted_text = page[start_idx + len(start_marker):]
            sections.append(extracted_text)
    
    if not sections:
        print("⚠️ No se encontraron secciones de movimientos en el estado de cuenta de Santander.")
        return pd.DataFrame()
    
    # Unir todas las secciones extraídas
    text = "\n".join(sections)
    lines = text.split('\n')
    if not lines:
        print("⚠️ No se encontraron líneas de movimientos.")
        return pd.DataFrame()
    
    movements = []
    date_pattern = re.compile(r'\d{2}-[A-Za-z]{3}-\d{4}')
    amount_pattern = re.compile(r'\d{1,3}(?:,\d{3})*\.\d{2}')
    
    for line in lines:
        if not isinstance(line, str):
            continue
        
        line = line.strip()
        if not line or end_marker in line:
            continue
        
        date_match = date_pattern.search(line)
        amount_matches = amount_pattern.findall(line)
        
        if not date_match or len(amount_matches) < 1:
            continue
        
        fecha = format_date_santander(date_match.group())
        
        try:
            monto = float(amount_matches[-2].replace(',', ''))
            saldo = float(amount_matches[-1].replace(',', '')) if len(amount_matches) > 1 else None
        except ValueError:
            continue
        
        descripcion = line.replace(date_match.group(), "").strip()
        for amt in amount_matches:
            descripcion = descripcion.replace(amt, "").strip()
        
        etiqueta_predicha = predecir_etiqueta(descripcion, monto)
        
        movements.append({
            "banco": "Santander",
            "fecha_operacion": fecha,
            "descripcion": descripcion,
            "referencia": None,
            "monto": monto,
            "saldo_operacion": saldo,
            "etiqueta": etiqueta_predicha
        })
    
    return pd.DataFrame(movements)

def format_date_banorte(date_str):
    try:
        return datetime.strptime(date_str, "%d-%b-%y").strftime("%Y-%m-%d")
    except ValueError:
        print(f"⚠️ Error al convertir fecha: {date_str} - Formato incorrecto")
        return None

def extract_banorte(text):
    lines = text.split('\n')
    movements = []

    date_pattern = re.compile(r'\d{2}-[A-Z]{3}-\d{2}')
    amount_pattern = re.compile(r'\d{1,3}(?:,\d{3})*\.\d{2}')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        date_match = date_pattern.match(line)
        if not date_match:
            continue

        fecha = format_date_banorte(date_match.group())
        if not fecha:
            continue

        remamining_line = line.replace(date_match.group(), "").strip()
        parts = remamining_line.split()

        amounts = [p for p in parts if amount_pattern.match(p)]

        if len(amounts) < 2:
            print(f"⚠️ No se encontraron montos en la línea: {line}")
            continue

        try:
            monto = float(amounts[-2].replace(',', ''))
            saldo = float(amounts[-1].replace(',', ''))
        except ValueError:
            print("⚠️ Error al convertir montos en la línea: {line}")

        descripcion = " ".join(parts[:-2])
       
        etiqueta_predicha = predecir_etiqueta(descripcion, monto)

        movements.append({
            "banco": "Banorte",
            "fecha_operacion": fecha,
            "descripcion": descripcion,
            "referencia": None,
            "monto": monto,
            "saldo_operacion": saldo,
            "etiqueta": etiqueta_predicha
        })

    return pd.DataFrame(movements)