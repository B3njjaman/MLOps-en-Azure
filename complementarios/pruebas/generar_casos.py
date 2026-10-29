"""Genera, con scikit-learn real, los casos que la lógica en JS de «Validación temporal» tiene que reproducir.

Uso, desde la raíz del repositorio:

    python complementarios/pruebas/generar_casos.py

Escribe complementarios/pruebas/casos/validacion.json, que lee pruebas/logica.test.js:

    tss         TimeSeriesSplit en muchas combinaciones de n, K, h, g y w, con sus errores
    holdout     el holdout temporal, con train_test_split(shuffle=False)
    kfold       KFold(shuffle=True, random_state=0): los grupos, para comprobar la asignación de la página
    fuga        la fuga de cada pliegue, calculada con numpy
    reentrenar  algunas configuraciones de la rejilla vueltas a entrenar desde cero, con su MAE por
                pliegue: la página no puede mostrar un número que este recálculo no reproduzca
"""

import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import sklearn
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold, TimeSeriesSplit, train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "datos"))
from generar_datos import clave, error_real, errores, tablas  # noqa: E402

CASOS = Path(__file__).with_name("casos")


def rangos(entrenamiento, prueba):
    """Los dos conjuntos como [inicio, fin): en estos esquemas son siempre intervalos."""
    for indices in (entrenamiento, prueba):
        assert len(indices) == 0 or indices[-1] - indices[0] + 1 == len(indices)
    ini = lambda a: int(a[0]) if len(a) else 0  # noqa: E731
    fin = lambda a: int(a[-1]) + 1 if len(a) else 0  # noqa: E731
    return {"entrenamiento": [ini(entrenamiento), fin(entrenamiento)], "prueba": [ini(prueba), fin(prueba)]}


def fuga(entrenamiento, prueba) -> float:
    """La fracción de días de prueba con algún día de entrenamiento posterior."""
    if len(entrenamiento) == 0:
        return 0.0
    return float(np.mean(prueba < entrenamiento.max()))


def casos_tss() -> list[dict]:
    casos = []
    # Muchos n chicos, para llegar a los bordes (pocos días, pocos pliegues), y pocos n grandes.
    chicos = product((2, 3, 5, 8, 10, 13, 20, 31, 50, 100), (1, 2, 3, 5, 7, 12), (None, 1, 3, 7, 30), (0, 1, 7), (None, 5, 30))
    grandes = product((365, 1000, 1454), (1, 2, 3, 5, 10, 12), (None, 7, 30, 90, 180), (0, 7, 30), (None, 30, 180, 365, 730))
    for n, K, h, g, w in [*chicos, *grandes]:
        caso = {"n": n, "K": K, "h": h, "g": g, "w": w}
        try:
            validacion = TimeSeriesSplit(n_splits=K, test_size=h, gap=g, max_train_size=w)
            pares = list(validacion.split(np.arange(n)))
            caso["pliegues"] = [rangos(e, p) for e, p in pares]
            caso["fuga"] = [fuga(e, p) for e, p in pares]
        except ValueError as e:
            caso["error"] = str(e)
        casos.append(caso)
    return casos


def casos_holdout() -> list[dict]:
    casos = []
    for n, h, g in product((10, 100, 1454), (1, 3, 30, 90, 365), (0, 1, 7, 30)):
        if h >= n or h + g >= n:
            continue
        entrenamiento, prueba = train_test_split(np.arange(n), test_size=h, shuffle=False)
        entrenamiento = entrenamiento[: len(entrenamiento) - g]
        casos.append({"n": n, "h": h, "g": g, **rangos(entrenamiento, prueba), "fuga": fuga(entrenamiento, prueba)})
    return casos


def casos_kfold() -> list[dict]:
    casos = []
    for n, K in product((10, 53, 1454), (2, 3, 5, 10)):
        asignacion = np.empty(n, dtype=int)
        pares = list(KFold(n_splits=K, shuffle=True, random_state=0).split(np.arange(n)))
        for k, (_, prueba) in enumerate(pares):
            asignacion[prueba] = k
        casos.append({
            "n": n, "K": K, "asignacion": asignacion.tolist(),
            "entrenamiento": [e.tolist() for e, _ in pares], "prueba": [p.tolist() for _, p in pares],
            "fuga": [fuga(e, p) for e, p in pares],
        })
    return casos


CONFIGURACIONES = [
    dict(esquema="aleatorio", K=3),
    dict(esquema="aleatorio", K=5),
    dict(esquema="holdout", h=365, g=0),
    dict(esquema="holdout", h=90, g=30),
    dict(esquema="creciente", K=5, h=90, g=7),
    dict(esquema="creciente", K=3, h=180, g=30),
    dict(esquema="deslizante", K=5, h=90, g=7, w=365),
    dict(esquema="deslizante", K=10, h=30, g=0, w=180),
]


def reentrenar() -> dict:
    """Vuelve a entrenar desde cero algunas configuraciones, armando los pliegues aparte de generar_datos."""
    _, X, y, X26, y26 = tablas()
    n = len(X)
    salida = []
    for c in CONFIGURACIONES:
        K, h, g, w = c.get("K"), c.get("h"), c.get("g"), c.get("w")
        if c["esquema"] == "aleatorio":
            pares = list(KFold(n_splits=K, shuffle=True, random_state=0).split(X))
        elif c["esquema"] == "holdout":
            entrenamiento, prueba = train_test_split(np.arange(n), test_size=h, shuffle=False)
            pares = [(entrenamiento[: len(entrenamiento) - g], prueba)]
        else:
            pares = list(TimeSeriesSplit(n_splits=K, test_size=h, gap=g, max_train_size=w).split(X))
        maes = errores(pares, X, y)
        salida.append({
            "clave": clave(**c), "mae": maes, "estimacion": float(np.mean(maes)),
            "fuga": float(np.mean([fuga(e, p) for e, p in pares])),
        })
    return {"configuraciones": salida, "real2026": error_real(X, y, X26, y26)}


def main() -> None:
    CASOS.mkdir(exist_ok=True)
    datos = {
        "sklearn": sklearn.__version__,
        "tss": casos_tss(),
        "holdout": casos_holdout(),
        "kfold": casos_kfold(),
        "reentrenar": reentrenar(),
    }
    ruta = CASOS / "validacion.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(ruta, len(datos["tss"]), "casos de TimeSeriesSplit,", len(datos["holdout"]), "de holdout,", len(datos["kfold"]), "de KFold")


if __name__ == "__main__":
    main()
