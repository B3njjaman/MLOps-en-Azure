// Compara la lógica en JS de «Validación temporal» con los casos que generó scikit-learn real,
// y los errores precalculados de la página con un reentrenamiento hecho aparte.
// Uso, desde la raíz:  node --test "complementarios/pruebas/*.test.js"
// Para regenerar los casos:  python complementarios/pruebas/generar_casos.py

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { DATOS } from "../datos/validacion.js";
import {
  ValueError, claveRejilla, desdeClave, evaluar, fechaDelDia, fuga, fugaDelPliegue, media, pliegues,
  plieguesAleatorios, plieguesHoldout, plieguesTimeSeriesSplit, respetaElTiempo,
} from "../logica/validacion.js";

const casos = JSON.parse(readFileSync(new URL("./casos/validacion.json", import.meta.url), "utf-8"));
const cerca = (a, b, mensaje) => assert.ok(Math.abs(a - b) < 1e-9, `${mensaje}: ${a} ≠ ${b}`);

/** [inicio, fin) de un conjunto de días; falla si no es un intervalo. */
function comoRango(dias) {
  if (dias.length === 0) return [0, 0];
  assert.equal(dias[dias.length - 1] - dias[0] + 1, dias.length, "debería ser un intervalo");
  return [dias[0], dias[dias.length - 1] + 1];
}

test("TimeSeriesSplit: los pliegues, los errores y la fuga son los de scikit-learn", () => {
  assert.ok(casos.tss.length > 3000);
  let conError = 0;
  for (const c of casos.tss) {
    const nombre = JSON.stringify({ n: c.n, K: c.K, h: c.h, g: c.g, w: c.w });
    if (c.error) {
      conError += 1;
      assert.throws(() => plieguesTimeSeriesSplit(c.n, c), (e) => e instanceof ValueError && e.message === c.error, nombre);
      continue;
    }
    const mios = plieguesTimeSeriesSplit(c.n, c);
    assert.deepEqual(mios.map((p) => ({ entrenamiento: comoRango(p.entrenamiento), prueba: comoRango(p.prueba) })), c.pliegues, nombre);
    mios.forEach((p, k) => cerca(fugaDelPliegue(p), c.fuga[k], nombre));
  }
  assert.ok(conError > 500 && conError < casos.tss.length - 500, `casos con error: ${conError}`);
});

test("holdout temporal: igual que train_test_split(shuffle=False) con la separación descontada", () => {
  assert.ok(casos.holdout.length >= 40);
  for (const c of casos.holdout) {
    const [p] = plieguesHoldout(c.n, c.h, c.g);
    const nombre = JSON.stringify({ n: c.n, h: c.h, g: c.g });
    assert.deepEqual({ entrenamiento: comoRango(p.entrenamiento), prueba: comoRango(p.prueba) }, { entrenamiento: c.entrenamiento, prueba: c.prueba }, nombre);
    cerca(fugaDelPliegue(p), c.fuga, nombre);
    assert.equal(fugaDelPliegue(p), 0, nombre);
  }
  assert.throws(() => plieguesHoldout(10, 8, 2), ValueError);
  assert.throws(() => plieguesHoldout(10, 0), ValueError);
  assert.throws(() => plieguesTimeSeriesSplit(10, { K: 2, h: 0 }), ValueError);
});

test("KFold con mezcla: los pliegues armados desde la asignación son los de scikit-learn", () => {
  for (const c of casos.kfold) {
    const nombre = `n=${c.n} K=${c.K}`;
    const mios = plieguesAleatorios(c.asignacion, c.K);
    assert.deepEqual(mios.map((p) => p.entrenamiento), c.entrenamiento, nombre);
    assert.deepEqual(mios.map((p) => p.prueba), c.prueba, nombre);
    cerca(fuga(mios), media(c.fuga), nombre);
  }
});

test("la asignación de KFold que trae la página es la de KFold(n_splits=K, shuffle=True, random_state=0)", () => {
  for (const K of DATOS.rejilla.KS) {
    const c = casos.kfold.find((x) => x.n === DATOS.meta.n && x.K === K);
    assert.ok(c, `falta el caso n=${DATOS.meta.n} K=${K}`);
    assert.deepEqual(DATOS.asignacion[String(K)], c.asignacion, `K=${K}`);
  }
});

test("respeta el tiempo: los esquemas temporales sí y el aleatorio no", () => {
  const { n } = DATOS.meta;
  const asignacion = DATOS.asignacion;
  assert.equal(respetaElTiempo(pliegues("aleatorio", { K: 5 }, { n, asignacion })), false);
  assert.equal(respetaElTiempo(pliegues("holdout", { h: 365, g: 0 }, { n, asignacion })), true);
  assert.equal(respetaElTiempo(pliegues("creciente", { K: 5, h: 90, g: 7 }, { n, asignacion })), true);
  assert.equal(respetaElTiempo(pliegues("deslizante", { K: 5, h: 90, g: 7, w: 365 }, { n, asignacion })), true);
});

test("la fuga del aleatorio es casi total y la de los esquemas temporales es cero", () => {
  const { n } = DATOS.meta;
  const asignacion = DATOS.asignacion;
  assert.ok(fuga(pliegues("aleatorio", { K: 5 }, { n, asignacion })) > 0.9);
  assert.equal(fuga(pliegues("creciente", { K: 10, h: 30, g: 0 }, { n, asignacion })), 0);
});

test("la rejilla: cada configuración tiene un MAE por pliegue, y las que scikit-learn rechaza no están", () => {
  const { n } = DATOS.meta;
  const { KS, HS_HOLDOUT, HS, GS, WS } = DATOS.rejilla;
  let vistas = 0;
  const probar = (esquema, p, pliegues_) => {
    const r = evaluar(esquema, p, DATOS);
    if (r.error) {
      assert.equal(DATOS.mae[claveRejilla(esquema, p)], undefined, claveRejilla(esquema, p));
      return;
    }
    vistas += 1;
    // Sin fuga y respetar el tiempo son lo mismo: los conjuntos son disjuntos.
    assert.equal(r.fuga === 0, r.respeta, claveRejilla(esquema, p));
    assert.equal(r.respeta, esquema !== "aleatorio", claveRejilla(esquema, p));
    assert.equal(r.maes?.length, pliegues_, claveRejilla(esquema, p));
    cerca(r.estimacion, media(r.maes), "estimación");
  };
  for (const K of KS) probar("aleatorio", { K }, K);
  for (const h of HS_HOLDOUT) for (const g of GS) probar("holdout", { h, g }, 1);
  for (const K of KS) for (const h of HS) for (const g of GS) {
    probar("creciente", { K, h, g }, K);
    for (const w of WS) probar("deslizante", { K, h, g, w }, K);
  }
  assert.equal(vistas, Object.keys(DATOS.mae).length, "toda entrada de la rejilla se usa");
  assert.equal(n, 1454);
});

test("los errores precalculados son los de un reentrenamiento hecho aparte", () => {
  for (const c of casos.reentrenar.configuraciones) {
    const { esquema, parametros } = desdeClave(c.clave);
    assert.equal(claveRejilla(esquema, parametros), c.clave);
    const r = evaluar(esquema, parametros, DATOS);
    assert.equal(r.maes.length, c.mae.length, c.clave);
    r.maes.forEach((m, k) => cerca(m, c.mae[k], `${c.clave} pliegue ${k}`));
    cerca(r.estimacion, c.estimacion, `${c.clave} R̂`);
    cerca(r.fuga, c.fuga, `${c.clave} fuga`);
  }
  cerca(DATOS.real2026, casos.reentrenar.real2026, "error real 2026");
  assert.equal(casos.reentrenar.configuraciones.length, 8);
});

test("las fechas: el día 0 es el 1 de enero de 2022 y el 1461 el 1 de enero de 2026", () => {
  assert.equal(fechaDelDia(0), "2022-01-01");
  assert.equal(fechaDelDia(7), "2022-01-08");
  assert.equal(fechaDelDia(1460), "2025-12-31");
  assert.equal(fechaDelDia(1461), "2026-01-01");
  assert.equal(DATOS.consumo.length, 1461 + 365);
  assert.equal(DATOS.meta.n, DATOS.meta.dias_historia - DATOS.meta.descartados);
});
