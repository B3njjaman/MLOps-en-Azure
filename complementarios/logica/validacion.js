// Los esquemas de validación de la lección 3: los pliegues (E_k, P_k) de cada uno, el error
// que promete y cuánto futuro ve el entrenamiento. Es la parte de la simulación que no dibuja:
// se prueba en Node contra scikit-learn (complementarios/pruebas/logica.test.js).
//
// Un pliegue es { entrenamiento, prueba }: las posiciones de los días, de 0 a n−1, en orden.

/** Un error que en Python lanzaría scikit-learn, con su mismo mensaje. */
export class ValueError extends Error {
  constructor(mensaje) {
    super(mensaje);
    this.tipo = "ValueError";
  }
}

/** Los enteros de a (incluido) a b (excluido). */
const rango = (a, b) => Array.from({ length: Math.max(0, b - a) }, (_, i) => a + i);

/**
 * TimeSeriesSplit(n_splits=K, test_size=h, gap=g, max_train_size=w) sobre n días.
 * Con h = null, scikit-learn toma n // (K + 1). Con w = null, la ventana crece.
 */
export function plieguesTimeSeriesSplit(n, { K, h = null, g = 0, w = null }) {
  if (!Number.isInteger(K) || K < 2) {
    throw new ValueError(`k-fold cross-validation requires at least one train/test split by setting n_splits=2 or more, got n_splits=${K}.`);
  }
  if (h !== null && (!Number.isInteger(h) || h < 1)) {
    throw new ValueError(`h tiene que ser un entero de 1 o más, no ${h}.`);
  }
  const prueba = h ?? Math.floor(n / (K + 1));
  if (K + 1 > n) {
    throw new ValueError(`Cannot have number of folds=${K + 1} greater than the number of samples=${n}.`);
  }
  if (n - g - prueba * K <= 0) {
    throw new ValueError(`Too many splits=${K} for number of samples=${n} with test_size=${prueba} and gap=${g}.`);
  }
  const pliegues = [];
  for (let inicio = n - K * prueba; inicio < n; inicio += prueba) {
    const finEntrenamiento = inicio - g;
    const desde = w && w < finEntrenamiento ? finEntrenamiento - w : 0;
    pliegues.push({ entrenamiento: rango(desde, finEntrenamiento), prueba: rango(inicio, inicio + prueba) });
  }
  return pliegues;
}

/** Holdout temporal: se prueba en los últimos h días y se entrena con los anteriores a la separación. */
export function plieguesHoldout(n, h, g = 0) {
  if (!Number.isInteger(h) || h < 1) {
    throw new ValueError(`h tiene que ser un entero de 1 o más, no ${h}.`);
  }
  const corte = n - h;
  if (corte - g <= 0) {
    throw new ValueError(`Con n=${n}, h=${h} y g=${g} no queda ningún día para entrenar.`);
  }
  return [{ entrenamiento: rango(0, corte - g), prueba: rango(corte, n) }];
}

/**
 * KFold(n_splits=K, shuffle=True, random_state=0): el reparto de los días en grupos lo hace el
 * generador de numpy, que JavaScript no replica. Viene de Python como `asignacion[t]` = grupo del día t.
 */
export function plieguesAleatorios(asignacion, K) {
  const pliegues = [];
  for (let k = 0; k < K; k++) {
    const entrenamiento = [];
    const prueba = [];
    asignacion.forEach((grupo, t) => (grupo === k ? prueba : entrenamiento).push(t));
    pliegues.push({ entrenamiento, prueba });
  }
  return pliegues;
}

/** Los pliegues de un esquema ("aleatorio", "holdout", "creciente" o "deslizante"). */
export function pliegues(esquema, { K, h, g, w }, { n, asignacion }) {
  if (esquema === "aleatorio") return plieguesAleatorios(asignacion[String(K)], K);
  if (esquema === "holdout") return plieguesHoldout(n, h, g);
  if (esquema === "creciente") return plieguesTimeSeriesSplit(n, { K, h, g });
  return plieguesTimeSeriesSplit(n, { K, h, g, w });
}

/** El esquema respeta el tiempo si max E_k < min P_k en todos los pliegues. */
export function respetaElTiempo(plieguesDelEsquema) {
  return plieguesDelEsquema.every((p) => Math.max(...p.entrenamiento) < Math.min(...p.prueba));
}

/** Los días de prueba que tienen algún día de entrenamiento posterior: futuro que el modelo vio. */
export function diasConFuga(pliegue) {
  const ultimo = pliegue.entrenamiento.length ? pliegue.entrenamiento[pliegue.entrenamiento.length - 1] : -1;
  return pliegue.prueba.filter((t) => t < ultimo);
}

/** La fracción de días de prueba de un pliegue que tiene fuga. */
export function fugaDelPliegue(pliegue) {
  return diasConFuga(pliegue).length / pliegue.prueba.length;
}

/** La fuga del esquema: el promedio de la de sus pliegues. */
export function fuga(plieguesDelEsquema) {
  return media(plieguesDelEsquema.map(fugaDelPliegue));
}

export function media(valores) {
  return valores.reduce((s, v) => s + v, 0) / valores.length;
}

/** La clave de una configuración en la rejilla; la misma que arma datos/generar_datos.py. */
export function claveRejilla(esquema, { K, h, g, w }) {
  const partes = { aleatorio: [K], holdout: [h, g], creciente: [K, h, g], deslizante: [K, h, g, w] }[esquema];
  return [esquema, ...partes].join("|");
}

/** Lo contrario de claveRejilla: "creciente|5|90|7" → { esquema, parametros: { K, h, g } }. */
export function desdeClave(clave) {
  const [esquema, ...resto] = clave.split("|");
  const n = resto.map(Number);
  const parametros = {
    aleatorio: { K: n[0] },
    holdout: { h: n[0], g: n[1] },
    creciente: { K: n[0], h: n[1], g: n[2] },
    deslizante: { K: n[0], h: n[1], g: n[2], w: n[3] },
  }[esquema];
  return { esquema, parametros };
}

/**
 * Todo lo que muestra la página de una configuración: los pliegues, el MAE de cada uno
 * (precalculado en Python con el modelo real), la estimación R̂ del esquema y la fuga.
 * Si scikit-learn no aceptaría la configuración, devuelve el error y nada más.
 */
export function evaluar(esquema, parametros, datos) {
  let pares;
  try {
    pares = pliegues(esquema, parametros, { n: datos.meta.n, asignacion: datos.asignacion });
  } catch (e) {
    if (e instanceof ValueError) return { error: e.message };
    throw e;
  }
  const maes = datos.mae[claveRejilla(esquema, parametros)];
  return {
    pliegues: pares,
    maes,
    estimacion: maes ? media(maes) : null,
    fuga: fuga(pares),
    respeta: respetaElTiempo(pares),
  };
}

/** La fecha ISO del día d, contado desde el 1 de enero de 2022 (d = 0). */
export function fechaDelDia(d, inicio = "2022-01-01") {
  const [a, m, dia] = inicio.split("-").map(Number);
  return new Date(Date.UTC(a, m - 1, dia + d)).toISOString().slice(0, 10);
}
