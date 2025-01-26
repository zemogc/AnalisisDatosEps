import pandas as pd
import matplotlib.pyplot as plt

def generar_excel(df):
    """
    Genera archivo Excel con datos procesados.
    
    Args:
        df (pandas.DataFrame): DataFrame a exportar
    """
    try:
        df.to_excel("reporte_eps.xlsx", index=False)
        print("Excel generado: reporte_eps.xlsx")
    except Exception as e:
        print(f"Error al generar Excel: {e}")

def graficar_datos(df):
    """
    Crea visualizaciones de los datos.
    
    Args:
        df (pandas.DataFrame): DataFrame con datos
    """
    plt.figure(figsize=(12, 6))
    
    # Gráfico de costos por diagnóstico
    costos_diagnostico = df.groupby('Diagnostico')['Costo_Total'].sum()
    costos_diagnostico.plot(kind='bar', color='skyblue')
    plt.title('Costo Total por Diagnóstico', fontsize=15)
    plt.ylabel('Costo Total ($)', fontsize=12)
    plt.xlabel('Diagnóstico', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('grafico_costos_diagnostico.png')
    plt.close()

    # Gráfico de distribución de costos por EPS
    plt.figure(figsize=(10, 6))
    costos_eps = df.groupby('EPS')['Costo_Total'].mean()
    costos_eps.plot(kind='pie', autopct='%1.1f%%')
    plt.title('Distribución de Costos Promedio por EPS', fontsize=15)
    plt.ylabel('')
    plt.tight_layout()
    plt.savefig('grafico_costos_eps.png')
    plt.close()

    print("Gráficos generados exitosamente.")
