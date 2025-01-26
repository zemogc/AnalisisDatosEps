from analysis import procesar_datos
from report import generar_excel, graficar_datos

def main():
    """Función principal que ejecuta el análisis y generación de reportes."""
    df = procesar_datos()
    if df is not None:
        generar_excel(df)
        graficar_datos(df)

if __name__ == "__main__":
    main()