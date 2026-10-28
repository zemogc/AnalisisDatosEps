"""Toma capturas del dashboard para la documentación.

Requiere el dashboard corriendo y Chrome instalado:

    streamlit run dashboard/app.py --server.headless true --server.port 8599
    python scripts/capturar_dashboard.py --url http://localhost:8599
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

DESTINO = Path(__file__).resolve().parents[1] / "docs" / "images"
PESTANAS = {
    "Pronóstico": "dashboard_pronostico.png",
    "Resumen": "dashboard_resumen.png",
    "EPS": "dashboard_eps.png",
    "Diagnósticos": "dashboard_diagnosticos.png",
    "Pacientes": "dashboard_pacientes.png",
}


def esperar_render(driver: webdriver.Chrome, segundos: float = 3.0) -> None:
    WebDriverWait(driver, 60).until(
        ec.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stMetric']"))
    )
    WebDriverWait(driver, 60).until_not(
        ec.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stStatusWidget'] svg"))
    )
    time.sleep(segundos)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8501")
    parser.add_argument("--ancho", type=int, default=1600)
    parser.add_argument("--alto", type=int, default=1450)
    args = parser.parse_args()

    opciones = webdriver.ChromeOptions()
    opciones.add_argument("--headless=new")
    opciones.add_argument(f"--window-size={args.ancho},{args.alto}")
    opciones.add_argument("--force-device-scale-factor=1")
    opciones.add_argument("--hide-scrollbars")
    driver = webdriver.Chrome(options=opciones)
    DESTINO.mkdir(parents=True, exist_ok=True)
    try:
        driver.get(args.url)
        esperar_render(driver, 5)
        for pestana, archivo in PESTANAS.items():
            boton = driver.find_element(
                By.XPATH, f"//*[@role='tab' and contains(normalize-space(.), '{pestana}')]"
            )
            boton.click()
            time.sleep(3)
            driver.save_screenshot(str(DESTINO / archivo))
            print(f"Captura: {DESTINO / archivo}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
