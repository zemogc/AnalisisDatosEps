import pyodbc
import pandas as pd

def conectar_bd():
    """Establece conexión con la base de datos SQL Server."""
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=ProyectoEPS;"
            "Trusted_Connection=yes;"
        )
        return conn
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

def obtener_datos(query):
    """
    Ejecuta consulta SQL y devuelve DataFrame de Pandas.
    
    Args:
        query (str): Consulta SQL a ejecutar
    
    Returns:
        pandas.DataFrame o None
    """
    conn = conectar_bd()
    if conn:
        try:
            # Usar read_sql para convertir directamente a DataFrame
            df = pd.read_sql(query, conn)
            return df
        except Exception as e:
            print(f"Error al ejecutar consulta: {e}")
        finally:
            conn.close()
    return None