import pandas as pd
import numpy as np
from database import obtener_datos

def procesar_datos():
    """
    Procesa datos de pacientes, consultas y medicamentos.
    
    Returns:
        pandas.DataFrame: Datos procesados con análisis estadístico
    """
    query = """
    SELECT 
        p.Nombre, 
        p.Edad, 
        p.Sexo, 
        p.EPS, 
        c.Diagnostico, 
        c.Costo AS Costo_Consulta, 
        c.Fecha_Consulta,
        m.Nombre_Medicamento, 
        m.Costo AS Costo_Medicamento
    FROM Pacientes p
    JOIN ConsultasMedicas c ON p.ID_Paciente = c.ID_Paciente
    JOIN Medicamentos m ON c.ID_Consulta = m.ID_Consulta;
    """
    
    df = obtener_datos(query)
    
    if df is not None and not df.empty:
        # Cálculos estadísticos
        df['Costo_Total'] = df['Costo_Consulta'] + df['Costo_Medicamento']
        
        # Análisis descriptivo
        costos = df['Costo_Total'].to_numpy()
        print(f"Promedio de costos: ${np.mean(costos):,.2f}")
        print(f"Desviación estándar: ${np.std(costos):,.2f}")
        
        return df
    
    print("No se encontraron datos.")
    return None