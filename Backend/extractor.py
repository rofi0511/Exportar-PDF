import pdfplumber
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


