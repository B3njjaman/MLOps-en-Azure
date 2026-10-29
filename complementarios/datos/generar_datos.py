"""Precalcula los errores de la simulación «Validación temporal» con el modelo real de la lección.

Uso, desde la raíz del repositorio:

    python complementarios/datos/generar_datos.py

Escribe complementarios/datos/validacion.json y complementarios/datos/validacion.js (el mismo
contenido como módulo, que es lo que empaqueta la página). Entrena el RandomForestRegressor de
la lección una vez por pliegue de cada configuración de la rejilla: unos 560 entrenamientos.

La rejilla (cada esquema usa solo los parámetros que le corresponden):

    aleatorio    K ∈ {3, 5, 10}
    holdout      h ∈ {30, 90, 180, 365},  g ∈ {0, 7, 30}
    creciente    K ∈ {3, 5, 10},  h ∈ {30, 90, 180},  g ∈ {0, 7, 30}
    deslizante   lo mismo que creciente,  w ∈ {180, 365, 730}

Las combinaciones en que scikit-learn no cabe (K·h + g ≥ n) no se entrenan: la página muestra
el ValueError.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold, TimeSeriesSplit

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "modulos" / "modulo-1"))
from planta import futuro, historia  # noqa: E402

CARPETA = Path(__file__).resolve().parent

KS = (3, 5, 10)
HS_HOLDOUT = (30, 90, 180, 365)
HS = (30, 90, 180)
GS = (0, 7, 30)
WS = (180, 365, 730)


def variables(df: pd.DataFrame) -> pd.DataFrame:
    """Las variables de la lección. Los rezagos se calculan sobre la serie que se le pase."""
    return pd.DataFrame(
        {
            "dia_semana": df["fecha"].dt.dayofweek,
            "produccion": df["produccion"],
            "temperatura_pronostico": df["temperatura_pronostico"],
            "consumo_ayer": df["consumo"].shift(1),
            "consumo_semana_pasada": df["consumo"].shift(7),
        }
    )


def tablas():
    """(X, y) de la historia sin los 7 primeros días, y (X, y) de 2026 con rezagos de la serie completa."""
    hist, fut = historia(), futuro()
    completa = pd.concat([hist, fut], ignore_index=True)
    X_todo = variables(completa)
    y_todo = completa["consumo"]
    en_historia = (completa["fecha"] < "2026-01-01") & X_todo.notna().all(axis=1)
    en_2026 = completa["fecha"] >= "2026-01-01"
    X, y = X_todo[en_historia].reset_index(drop=True), y_todo[en_historia].reset_index(drop=True)
    X26, y26 = X_todo[en_2026].reset_index(drop=True), y_todo[en_2026].reset_index(drop=True)
    return completa, X, y, X26, y26


def pliegues_de(esquema, n, K, h, g, w):
    """Los pares (entrenamiento, prueba) de un esquema, con las posiciones de los días 0 … n−1."""
    if esquema == "aleatorio":
        validacion = KFold(n_splits=K, shuffle=True, random_state=0)
        pares = list(validacion.split(np.arange(n)))
    elif esquema == "creciente":
        validacion = TimeSeriesSplit(n_splits=K, test_size=h, gap=g)
        pares = list(validacion.split(np.arange(n)))
    elif esquema == "deslizante":
        validacion = TimeSeriesSplit(
            n_splits=K, test_size=h, gap=g, max_train_size=w
        )
        pares = list(validacion.split(np.arange(n)))
    else:  # holdout temporal
        corte = n - h
        entrenamiento = np.arange(0, corte - g)
        prueba = np.arange(corte, n)
        pares = [(entrenamiento, prueba)]
    return pares


def errores(pares, X, y):
    """El MAE de cada pliegue: se entrena un modelo nuevo con el entrenamiento y se prueba en la prueba."""
    maes = []
    for entrenamiento, prueba in pares:
        modelo = RandomForestRegressor(n_estimators=200, random_state=0, n_jobs=-1)
        modelo.fit(X.iloc[entrenamiento], y.iloc[entrenamiento])
        predicho = modelo.predict(X.iloc[prueba])
        maes.append(mean_absolute_error(y.iloc[prueba], predicho))
    return maes


def error_real(X, y, X26, y26):
    """El MAE en 2026 del modelo entrenado con toda la historia."""
    modelo = RandomForestRegressor(n_estimators=200, random_state=0, n_jobs=-1)
    modelo.fit(X, y)
    return mean_absolute_error(y26, modelo.predict(X26))


def clave(esquema, K=None, h=None, g=None, w=None):
    """La clave de una configuración; la misma que arma logica/validacion.js."""
    partes = {
        "aleatorio": [K],
        "holdout": [h, g],
        "creciente": [K, h, g],
        "deslizante": [K, h, g, w],
    }[esquema]
    return "|".join([esquema, *map(str, partes)])


def configuraciones(n):
    """Todas las configuraciones de la rejilla que scikit-learn acepta con n días."""
    for K in KS:
        yield dict(esquema="aleatorio", K=K)
    for h in HS_HOLDOUT:
        for g in GS:
            yield dict(esquema="holdout", h=h, g=g)
    for K in KS:
        for h in HS:
            for g in GS:
                if n - g - K * h <= 0:
                    continue
                yield dict(esquema="creciente", K=K, h=h, g=g)
                for w in WS:
                    yield dict(esquema="deslizante", K=K, h=h, g=g, w=w)


def main() -> None:
    import sklearn

    completa, X, y, X26, y26 = tablas()
    n = len(X)
    configs = list(configuraciones(n))
    entrenamientos = sum(1 if c["esquema"] == "holdout" else c["K"] for c in configs)
    print(f"n = {n}, {len(configs)} configuraciones, {entrenamientos} entrenamientos")

    asignacion = {}
    for K in KS:
        a = np.empty(n, dtype=int)
        for k, (_, prueba) in enumerate(KFold(n_splits=K, shuffle=True, random_state=0).split(np.arange(n))):
            a[prueba] = k
        asignacion[str(K)] = a.tolist()

    mae = {}
    for i, c in enumerate(configs, 1):
        pares = pliegues_de(c["esquema"], n, c.get("K"), c.get("h"), c.get("g"), c.get("w"))
        mae[clave(**c)] = errores(pares, X, y)
        if i % 25 == 0:
            print(f"{i}/{len(configs)}", flush=True)

    real = error_real(X, y, X26, y26)
    datos = {
        "meta": {
            "inicio": "2022-01-01",
            "dias_historia": 1461,
            "descartados": 7,
            "n": n,
            "sklearn": sklearn.__version__,
            "modelo": "RandomForestRegressor(n_estimators=200, random_state=0, n_jobs=-1)",
        },
        "consumo": completa["consumo"].tolist(),
        "real2026": real,
        "asignacion": asignacion,
        "rejilla": {"KS": KS, "HS_HOLDOUT": HS_HOLDOUT, "HS": HS, "GS": GS, "WS": WS},
        "mae": mae,
    }
    texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    (CARPETA / "validacion.json").write_text(texto + "\n", encoding="utf-8")
    (CARPETA / "validacion.js").write_text(
        "// Generado por complementarios/datos/generar_datos.py. No se edita a mano.\n"
        f"export const DATOS = {texto};\n",
        encoding="utf-8",
    )
    print(f"error real 2026: {real:.4f}")
    print(f"{len(mae)} configuraciones guardadas")


if __name__ == "__main__":
    main()
