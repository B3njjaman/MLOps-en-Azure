"""La planta del curso: consumo eléctrico diario simulado.

Una planta industrial produce cada día según un plan y consume electricidad según
lo que produce, la temperatura y el desgaste de sus equipos. Los datos son
sintéticos a propósito: como se conoce el proceso que los genera, se puede medir
cuánto se equivoca un modelo en un futuro que el modelo no vio.

Cada día t (contado desde el 1 de enero de 2022) tiene:

    fecha                    el día
    produccion               toneladas planificadas para el día (se conoce de antemano)
    temperatura_pronostico   °C, el pronóstico publicado la tarde anterior
    temperatura              °C, la temperatura media que hubo (se conoce al terminar el día)
    consumo                  MWh consumidos en el día (se conoce al terminar el día)

El proceso, con d(t) el día del año y x⁺ = max(x, 0):

    τ_t  = 14 + 7·cos(2π(d(t) − 15)/365,25) + a_t,     a_t = 0,7·a_{t−1} + ξ_t,   ξ_t ~ N(0, 1,6²)
    τ̂_t = τ_t + ζ_t,                                    ζ_t ~ N(0, 2²)
    y_t  = 60 + 0,07·p_t + 4·(τ_t − 16)⁺ + 3·(10 − τ_t)⁺ + 0,02·t + u_t,
           u_t = 0,6·u_{t−1} + ε_t,                      ε_t ~ N(0, 5²)

La producción planificada p_t es de 3000 t de lunes a sábado y 2300 t el domingo,
baja a 400 t en dos paradas de mantención al año (6 días desde el 10 de abril y
desde el 2 de octubre) y tiene un ruido de N(0, 60²) t, que en las paradas es N(0, 30²) t.

Uso:

    from planta import historia, futuro
    df = historia()   # 2022-01-01 a 2025-12-31: lo que hay para entrenar
    nuevo = futuro()  # 2026: lo que la planta vive después, día a día
"""

from __future__ import annotations

import numpy as np
import pandas as pd

INICIO = "2022-01-01"
CORTE = "2026-01-01"  # desde este día empieza el futuro
FIN = "2026-12-31"
SEMILLA = 7

PARADAS = (("04-10", 6), ("10-02", 6))  # (mes-día de inicio, días) de cada parada anual


def _ar1(rng: np.random.Generator, n: int, phi: float, sigma: float) -> np.ndarray:
    """Un proceso AR(1) estacionario: z_t = φ·z_{t−1} + ruido, que parte en su distribución estacionaria."""
    ruido = rng.normal(0.0, sigma, n)
    z = np.empty(n)
    z[0] = ruido[0] / np.sqrt(1.0 - phi**2)
    for t in range(1, n):
        z[t] = phi * z[t - 1] + ruido[t]
    return z


def _en_parada(fechas: pd.DatetimeIndex) -> np.ndarray:
    parada = np.zeros(len(fechas), dtype=bool)
    for anio in sorted(set(fechas.year)):
        for inicio, dias in PARADAS:
            desde = pd.Timestamp(f"{anio}-{inicio}")
            parada |= (fechas >= desde) & (fechas < desde + pd.Timedelta(days=dias))
    return parada


def generar(inicio: str = INICIO, fin: str = FIN, semilla: int = SEMILLA) -> pd.DataFrame:
    """Simula la planta día a día entre `inicio` y `fin`, ambos incluidos.

    La misma semilla da siempre la misma tabla. El día t se cuenta desde INICIO,
    así que pedir un tramo más corto no cambia la tendencia, pero sí el ruido:
    para tramos de la misma simulación, usar `historia` y `futuro`.
    """
    fechas = pd.date_range(inicio, fin, freq="D")
    n = len(fechas)
    rng = np.random.default_rng(semilla)

    t = (fechas - pd.Timestamp(INICIO)).days.to_numpy()
    d = fechas.day_of_year.to_numpy()
    temperatura = 14 + 7 * np.cos(2 * np.pi * (d - 15) / 365.25) + _ar1(rng, n, 0.7, 1.6)
    pronostico = temperatura + rng.normal(0.0, 2.0, n)

    domingo = fechas.day_of_week.to_numpy() == 6
    produccion = np.where(domingo, 2300.0, 3000.0) + rng.normal(0.0, 60.0, n)
    produccion = np.where(_en_parada(fechas), 400.0 + rng.normal(0.0, 30.0, n), produccion)
    produccion = np.round(produccion)

    consumo = (
        60
        + 0.07 * produccion
        + 4.0 * np.maximum(temperatura - 16, 0)
        + 3.0 * np.maximum(10 - temperatura, 0)
        + 0.02 * t
        + _ar1(rng, n, 0.6, 5.0)
    )

    return pd.DataFrame(
        {
            "fecha": fechas,
            "produccion": produccion.astype(int),
            "temperatura_pronostico": pronostico.round(1),
            "temperatura": temperatura.round(1),
            "consumo": consumo.round(1),
        }
    )


def historia(semilla: int = SEMILLA) -> pd.DataFrame:
    """Los cuatro años que hay para entrenar: del 1 de enero de 2022 al 31 de diciembre de 2025."""
    df = generar(semilla=semilla)
    return df[df["fecha"] < CORTE].reset_index(drop=True)


def futuro(semilla: int = SEMILLA) -> pd.DataFrame:
    """2026: los días que la planta vive después de entrenar, de la misma simulación que `historia`."""
    df = generar(semilla=semilla)
    return df[df["fecha"] >= CORTE].reset_index(drop=True)
