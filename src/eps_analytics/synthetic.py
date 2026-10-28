"""Generador de datos sintéticos reproducibles para el modelo EPS.

Los datos no corresponden a personas reales. Las distribuciones buscan
parecerse al contexto colombiano: participación de mercado por EPS, régimen
contributivo/subsidiado, prevalencia de diagnósticos según edad, picos de
enfermedad respiratoria en las temporadas de lluvia y costos en pesos (COP)
con colas largas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

# EPS -> (participación de pacientes, multiplicador de tarifa)
EPS = {
    "Nueva EPS": (0.22, 0.92),
    "EPS Sura": (0.17, 1.10),
    "Sanitas": (0.14, 1.08),
    "Salud Total": (0.12, 1.00),
    "Compensar": (0.10, 1.05),
    "Famisanar": (0.09, 0.95),
    "Coosalud": (0.08, 0.88),
    "Mutual Ser": (0.08, 0.85),
}

# EPS con mayor proporción de afiliados al régimen subsidiado
PROB_SUBSIDIADO = {
    "Nueva EPS": 0.55,
    "Coosalud": 0.85,
    "Mutual Ser": 0.9,
    "Famisanar": 0.35,
}

CIUDADES = {
    "Bogotá": 0.30,
    "Medellín": 0.16,
    "Cali": 0.13,
    "Barranquilla": 0.10,
    "Cartagena": 0.07,
    "Bucaramanga": 0.07,
    "Pereira": 0.05,
    "Manizales": 0.04,
    "Cúcuta": 0.05,
    "Santa Marta": 0.03,
}

NOMBRES_F = [
    "María",
    "Luisa",
    "Ana",
    "Valentina",
    "Camila",
    "Daniela",
    "Laura",
    "Sofía",
    "Paula",
    "Carolina",
    "Natalia",
    "Andrea",
    "Gloria",
    "Martha",
    "Diana",
    "Juliana",
]
NOMBRES_M = [
    "Juan",
    "Carlos",
    "Andrés",
    "Santiago",
    "Sebastián",
    "Luis",
    "Jorge",
    "Felipe",
    "Diego",
    "Alejandro",
    "Miguel",
    "David",
    "Camilo",
    "Óscar",
    "Mateo",
    "Javier",
]
APELLIDOS = [
    "Rodríguez",
    "Gómez",
    "González",
    "Martínez",
    "García",
    "López",
    "Hernández",
    "Sánchez",
    "Ramírez",
    "Pérez",
    "Díaz",
    "Torres",
    "Rojas",
    "Vargas",
    "Moreno",
    "Castro",
    "Jiménez",
    "Ortiz",
    "Muñoz",
    "Restrepo",
    "Cárdenas",
    "Ospina",
]


@dataclass(frozen=True)
class Diagnostico:
    codigo: str
    nombre: str
    peso_base: float
    factor_costo: float
    # Multiplicador del peso por grupo etario: (0-17, 18-44, 45-64, 65+)
    perfil_edad: tuple[float, float, float, float]
    medicamentos: tuple[tuple[str, int], ...]
    respiratorio: bool = False
    solo_mujeres: bool = False


DIAGNOSTICOS = (
    Diagnostico(
        "J06.9",
        "Infección respiratoria aguda",
        1.6,
        0.8,
        (2.5, 1.0, 0.8, 1.1),
        (("Acetaminofén 500 mg", 4_500), ("Loratadina 10 mg", 6_800), ("Ambroxol jarabe", 12_900)),
        respiratorio=True,
    ),
    Diagnostico(
        "I10",
        "Hipertensión esencial",
        1.4,
        1.0,
        (0.0, 0.4, 2.2, 3.0),
        (("Losartán 50 mg", 9_800), ("Hidroclorotiazida 25 mg", 5_200), ("Amlodipino 5 mg", 8_400)),
    ),
    Diagnostico(
        "E11.9",
        "Diabetes mellitus tipo 2",
        1.0,
        1.4,
        (0.0, 0.3, 2.0, 2.4),
        (("Metformina 850 mg", 11_500), ("Insulina glargina", 98_000), ("Glibenclamida 5 mg", 6_300)),
    ),
    Diagnostico("Z00.0", "Control de salud preventivo", 1.3, 0.6, (1.5, 1.0, 1.0, 0.9), ()),
    Diagnostico(
        "M54.5",
        "Lumbalgia",
        1.0,
        0.9,
        (0.1, 1.4, 1.3, 0.9),
        (("Naproxeno 250 mg", 7_900), ("Metocarbamol 750 mg", 14_200)),
    ),
    Diagnostico(
        "K29.7",
        "Gastritis",
        0.8,
        0.85,
        (0.3, 1.3, 1.1, 0.9),
        (("Omeprazol 20 mg", 6_900), ("Esomeprazol 40 mg", 18_500)),
    ),
    Diagnostico(
        "A09",
        "Enfermedad diarreica aguda",
        0.7,
        0.8,
        (2.2, 0.8, 0.6, 1.0),
        (("Sales de rehidratación oral", 3_900), ("Zinc jarabe", 15_400)),
    ),
    Diagnostico(
        "N39.0",
        "Infección de vías urinarias",
        0.6,
        0.9,
        (0.6, 1.1, 1.0, 1.4),
        (("Nitrofurantoína 100 mg", 13_700), ("Cefalexina 500 mg", 16_200)),
    ),
    Diagnostico(
        "F41.1",
        "Trastorno de ansiedad generalizada",
        0.5,
        1.2,
        (0.4, 1.5, 1.0, 0.6),
        (("Sertralina 50 mg", 21_000), ("Clonazepam 2 mg", 12_300)),
    ),
    Diagnostico(
        "J45.9",
        "Asma",
        0.45,
        1.1,
        (1.8, 0.9, 0.8, 0.9),
        (("Salbutamol inhalador", 17_800), ("Beclometasona inhalador", 34_500)),
        respiratorio=True,
    ),
    Diagnostico(
        "I25.1",
        "Cardiopatía isquémica",
        0.25,
        4.5,
        (0.0, 0.1, 1.5, 3.5),
        (
            ("Ácido acetilsalicílico 100 mg", 3_600),
            ("Atorvastatina 40 mg", 19_800),
            ("Clopidogrel 75 mg", 24_900),
        ),
    ),
    Diagnostico(
        "C50.9",
        "Tumor maligno de mama",
        0.08,
        14.0,
        (0.0, 0.5, 2.0, 1.8),
        (("Tamoxifeno 20 mg", 58_000), ("Anastrozol 1 mg", 92_000)),
        solo_mujeres=True,
    ),
)

# Tipo de atención -> (probabilidad, costo base en COP)
TIPOS_ATENCION = {
    "Medicina general": (0.62, 48_000),
    "Especialista": (0.25, 125_000),
    "Urgencias": (0.13, 260_000),
}

# Prevalencia de condiciones crónicas por grupo etario (0-17, 18-44, 45-64, 65+).
# Un paciente con la condición vuelve a consultar por ella; uno sin ella casi nunca.
PREVALENCIA_CRONICA = {
    "I10": (0.0, 0.08, 0.30, 0.55),
    "E11.9": (0.0, 0.03, 0.14, 0.22),
    "J45.9": (0.08, 0.05, 0.05, 0.05),
    "F41.1": (0.02, 0.08, 0.07, 0.05),
    "I25.1": (0.0, 0.005, 0.04, 0.10),
    "C50.9": (0.0, 0.005, 0.02, 0.03),
}

# Meses con mayor carga respiratoria en Colombia (temporadas de lluvia)
MESES_LLUVIA = {4, 5, 10, 11}


def _grupo_edad(edad: np.ndarray) -> np.ndarray:
    return np.digitize(edad, [18, 45, 65])


def _elegir(rng: np.random.Generator, opciones: dict, n: int) -> np.ndarray:
    claves = list(opciones)
    pesos = np.array([v[0] if isinstance(v, tuple) else v for v in opciones.values()], float)
    return rng.choice(claves, size=n, p=pesos / pesos.sum())


def generar_pacientes(rng: np.random.Generator, n: int) -> pd.DataFrame:
    sexo = rng.choice(["F", "M"], size=n, p=[0.53, 0.47])
    # Mezcla de distribuciones para aproximar la pirámide poblacional
    edad = np.where(
        rng.random(n) < 0.22,
        rng.integers(0, 18, n),
        np.clip(rng.normal(42, 17, n), 18, 95),
    ).astype(int)
    nombres = np.where(sexo == "F", rng.choice(NOMBRES_F, n), rng.choice(NOMBRES_M, n))
    nombre_completo = [
        f"{nom} {a1} {a2}"
        for nom, a1, a2 in zip(nombres, rng.choice(APELLIDOS, n), rng.choice(APELLIDOS, n), strict=True)
    ]
    eps = _elegir(rng, EPS, n)
    p_sub = np.array([PROB_SUBSIDIADO.get(e, 0.15) for e in eps])
    regimen = np.where(rng.random(n) < p_sub, "Subsidiado", "Contributivo")
    return pd.DataFrame(
        {
            "ID_Paciente": np.arange(1, n + 1),
            "Nombre": nombre_completo,
            "Edad": edad,
            "Sexo": sexo,
            "EPS": eps,
            "Regimen": regimen,
            "Ciudad": _elegir(rng, CIUDADES, n),
        }
    )


def _fechas(rng: np.random.Generator, n: int, inicio: date, fin: date) -> pd.Series:
    dias = pd.date_range(inicio, fin, freq="D")
    # Menos atención ambulatoria en fines de semana y diciembre/enero
    peso = np.where(dias.day_of_week >= 5, 0.35, 1.0)
    peso *= np.where(dias.month.isin([12, 1]), 0.8, 1.0)
    # Mayor demanda en temporada de lluvias (picos respiratorios)
    peso *= np.where(dias.month.isin(list(MESES_LLUVIA)), 1.2, 1.0)
    return pd.Series(rng.choice(dias, size=n, p=peso / peso.sum()))


def generar_consultas(
    rng: np.random.Generator, pacientes: pd.DataFrame, inicio: date, fin: date
) -> pd.DataFrame:
    edad = pacientes["Edad"].to_numpy()
    grupo = _grupo_edad(edad)
    # Condiciones crónicas asignadas al paciente, no a cada consulta
    cronicos = [i for i, d in enumerate(DIAGNOSTICOS) if d.codigo in PREVALENCIA_CRONICA]
    prevalencia = np.array([PREVALENCIA_CRONICA[DIAGNOSTICOS[i].codigo] for i in cronicos])
    tiene = rng.random((len(pacientes), len(cronicos))) < prevalencia[:, grupo].T
    solo_mujeres = np.array([DIAGNOSTICOS[i].solo_mujeres for i in cronicos])
    tiene[:, solo_mujeres] &= (pacientes["Sexo"].to_numpy() == "F")[:, None]

    # Pacientes mayores y con más condiciones crónicas consultan más
    lam = np.array([2.4, 1.8, 2.6, 3.4])[grupo] * (fin - inicio).days / 365
    lam *= 1 + 0.6 * tiene.sum(axis=1)
    n_por_paciente = np.maximum(rng.poisson(lam), 1)
    idx = np.repeat(np.arange(len(pacientes)), n_por_paciente)
    n = len(idx)

    fechas = _fechas(rng, n, inicio, fin)
    meses = fechas.dt.month.to_numpy()
    grupo_c = grupo[idx]
    mujeres = (pacientes["Sexo"].to_numpy() == "F")[idx]

    # Matriz de pesos (consulta x diagnóstico) según edad, sexo y estación
    perfil = np.array([d.perfil_edad for d in DIAGNOSTICOS])  # (dx, 4)
    pesos = np.array([d.peso_base for d in DIAGNOSTICOS])[None, :] * perfil[:, grupo_c].T
    resp = np.array([d.respiratorio for d in DIAGNOSTICOS])
    pesos[np.ix_(np.isin(meses, list(MESES_LLUVIA)), resp)] *= 1.9
    pesos[np.ix_(~mujeres, np.array([d.solo_mujeres for d in DIAGNOSTICOS]))] = 0
    pesos[:, cronicos] = np.where(
        tiene[idx], np.maximum(pesos[:, cronicos] * 8.0, 2.0), pesos[:, cronicos] * 0.03
    )
    acumulado = (pesos / pesos.sum(axis=1, keepdims=True)).cumsum(axis=1)
    dx_idx = (rng.random((n, 1)) > acumulado).sum(axis=1)
    dx_idx = np.minimum(dx_idx, len(DIAGNOSTICOS) - 1)

    tipos = _elegir(rng, TIPOS_ATENCION, n)
    # Diagnósticos complejos se atienden más por especialista
    complejos = np.isin(dx_idx, [i for i, d in enumerate(DIAGNOSTICOS) if d.factor_costo > 3])
    tipos = np.where(complejos & (rng.random(n) < 0.7), "Especialista", tipos)

    base = np.array([TIPOS_ATENCION[t][1] for t in tipos], float)
    factor_dx = np.array([d.factor_costo for d in DIAGNOSTICOS])[dx_idx]
    factor_eps = np.array([EPS[e][1] for e in pacientes["EPS"].to_numpy()[idx]])
    costo = base * np.sqrt(factor_dx) * factor_eps * rng.lognormal(0, 0.35, n)
    # Procedimientos de alto costo esporádicos (cirugías, quimioterapia, UCI)
    eventos = rng.random(n) < 0.004 * factor_dx
    costo[eventos] *= rng.uniform(15, 60, eventos.sum())

    orden = np.argsort(fechas.to_numpy(), kind="stable")
    df = (
        pd.DataFrame(
            {
                "ID_Paciente": pacientes["ID_Paciente"].to_numpy()[idx],
                "Fecha_Consulta": fechas.dt.date.to_numpy(),
                "Tipo_Atencion": tipos,
                "Codigo_CIE10": [DIAGNOSTICOS[i].codigo for i in dx_idx],
                "Diagnostico": [DIAGNOSTICOS[i].nombre for i in dx_idx],
                "Costo": np.round(costo, -2),
            }
        )
        .iloc[orden]
        .reset_index(drop=True)
    )
    df.insert(0, "ID_Consulta", np.arange(1, n + 1))
    return df


def generar_medicamentos(rng: np.random.Generator, consultas: pd.DataFrame) -> pd.DataFrame:
    por_nombre = {d.nombre: d for d in DIAGNOSTICOS}
    filas = []
    for id_consulta, dx in zip(consultas["ID_Consulta"], consultas["Diagnostico"], strict=True):
        opciones = por_nombre[dx].medicamentos
        # ~15 % de las consultas no generan fórmula
        if not opciones or rng.random() < 0.15:
            continue
        k = rng.integers(1, len(opciones) + 1)
        for i in rng.choice(len(opciones), size=k, replace=False):
            nombre, precio = opciones[i]
            cantidad = int(rng.choice([1, 1, 2, 3]))
            costo = round(precio * cantidad * rng.uniform(0.9, 1.15), -2)
            filas.append((id_consulta, nombre, cantidad, costo))
    df = pd.DataFrame(filas, columns=["ID_Consulta", "Nombre_Medicamento", "Cantidad", "Costo"])
    df.insert(0, "ID_Medicamento", np.arange(1, len(df) + 1))
    return df


def generar_datos(
    n_pacientes: int = 2_000,
    seed: int = 42,
    inicio: date = date(2024, 1, 1),
    fin: date = date(2025, 12, 31),
) -> dict[str, pd.DataFrame]:
    """Genera las tres tablas del modelo. Misma semilla => mismos datos."""
    if n_pacientes <= 0:
        raise ValueError("n_pacientes debe ser positivo")
    if fin <= inicio:
        raise ValueError("La fecha final debe ser posterior a la inicial")
    rng = np.random.default_rng(seed)
    pacientes = generar_pacientes(rng, n_pacientes)
    consultas = generar_consultas(rng, pacientes, inicio, fin)
    medicamentos = generar_medicamentos(rng, consultas)
    return {"Pacientes": pacientes, "ConsultasMedicas": consultas, "Medicamentos": medicamentos}
