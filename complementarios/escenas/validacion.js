// Escena de la simulación 3: la serie de consumo, los pliegues de cada esquema de validación
// y lo que el esquema promete frente a lo que el modelo entrega en 2026.

import { DATOS } from "../datos/validacion.js";
import { desdeClave, diasConFuga, evaluar, fechaDelDia } from "../logica/validacion.js";
import { FUENTES, colores, iniciarPagina, lienzo, rotulo, segmentado } from "../motor.js";

iniciarPagina();

const $ = (sel) => document.querySelector(sel);

const { n, descartados } = DATOS.meta;
const TOTAL = DATOS.consumo.length; // 2022-01-01 a 2026-12-31
const DIA_2026 = DATOS.meta.dias_historia; // el día 1461 es el 1 de enero de 2026
const { KS, HS_HOLDOUT, HS, GS, WS } = DATOS.rejilla;

// ── Estado de los controles ──────────────────────────────────────────────────

const ESQUEMAS = [
  ["aleatorio", "Aleatorio"],
  ["holdout", "Holdout temporal"],
  ["creciente", "Origen móvil"],
  ["deslizante", "Ventana deslizante"],
];
const USA = { aleatorio: ["K"], holdout: ["h", "g"], creciente: ["K", "h", "g"], deslizante: ["K", "h", "g", "w"] };
const PREDETERMINADOS = {
  aleatorio: { K: 5 },
  holdout: { h: 365, g: 0 },
  creciente: { K: 5, h: 90, g: 7 },
  deslizante: { K: 5, h: 90, g: 7, w: 365 },
};
const valoresDe = (esquema) => ({ K: KS, g: GS, h: esquema === "holdout" ? HS_HOLDOUT : HS, w: WS });

const opciones = { esquema: "aleatorio", ...PREDETERMINADOS.aleatorio };
let estado = null;

const numero = (x, d = 1) => x.toFixed(d).replace(".", ",");
const porcentaje = (x) => `${Math.round(x * 100)} %`;
const parametrosActuales = () => Object.fromEntries(USA[opciones.esquema].map((p) => [p, opciones[p]]));

// ── Estado de cada día en cada pliegue ───────────────────────────────────────

const VACIO = 0;
const ENTRENA = 1;
const PRUEBA = 2;
const FUGA = 3;
const SEPARA = 4;

/** Qué es cada uno de los n días en un pliegue: entrena, separación, prueba (con o sin fuga) o sin usar. */
function estadosDelPliegue(pliegue) {
  const e = new Uint8Array(n);
  pliegue.entrenamiento.forEach((t) => (e[t] = ENTRENA));
  pliegue.prueba.forEach((t) => (e[t] = PRUEBA));
  diasConFuga(pliegue).forEach((t) => (e[t] = FUGA));
  const g = opciones.esquema === "aleatorio" ? 0 : opciones.g ?? 0;
  const primero = pliegue.prueba[0];
  for (let t = Math.max(0, primero - g); t < primero; t++) if (e[t] === VACIO) e[t] = SEPARA;
  return e;
}

// ── Dibujo de la serie y los pliegues ────────────────────────────────────────

const canvas = $("#stage");
const canvasBarras = $("#barras");

const ROTULOS_LEYENDA = ["entrenamiento", "separación", "prueba", "prueba con fuga", "sin usar"];
const coloresLeyenda = (c) => [c.celeste, c.violeta, c.ambar, c.rosa, c.borde2];

/** Reparte los rótulos de la leyenda en líneas, con un ancho de carácter fijo para no depender del canvas. */
function lineasDeLeyenda(ancho, margen, caracter) {
  const lineas = [[]];
  let x = margen;
  ROTULOS_LEYENDA.forEach((texto, i) => {
    const w = 18 + texto.length * caracter + 14;
    if (x + w > ancho - 8 && lineas[lineas.length - 1].length) {
      lineas.push([]);
      x = margen;
    }
    lineas[lineas.length - 1].push({ texto, i, x });
    x += w;
  });
  return lineas;
}

function disposicion(ancho) {
  const angosto = ancho < 560;
  const margen = angosto ? 26 : 38;
  const derecha = angosto ? 8 : 14;
  const arriba = 34;
  const altoSerie = angosto ? 92 : 124;
  const lineas = lineasDeLeyenda(ancho, margen, angosto ? 6 : 6.6);
  const filas = estado?.pliegues?.length ?? 0;
  const filaAlto = angosto ? 14 : 17;
  const separacion = angosto ? 3 : 4;
  const yLeyenda = arriba + altoSerie + 30;
  const yFilas = yLeyenda + lineas.length * 18 + 6;
  const alto = yFilas + filas * (filaAlto + separacion) + 12;
  return { angosto, margen, derecha, arriba, altoSerie, lineas, filaAlto, separacion, yLeyenda, yFilas, alto };
}

const vistaEscena = lienzo(canvas, {
  alto: (ancho) => disposicion(ancho).alto,
  dibujar: (ctx, ancho, alto) => dibujarEscena(ctx, ancho, alto),
});

function dibujarEscena(ctx, ancho, alto) {
  const c = colores();
  const d = disposicion(ancho);
  const x = (dia) => d.margen + (dia / (TOTAL - 1)) * (ancho - d.margen - d.derecha);
  const letra = d.angosto ? 9.5 : 10.5;

  ctx.fillStyle = c.fondo2;
  ctx.fillRect(0, 0, ancho, alto);

  // 2026: el futuro, que el modelo no ve al entrenar
  ctx.save();
  ctx.globalAlpha = 0.55;
  ctx.fillStyle = c.ambarSuave;
  ctx.fillRect(x(DIA_2026), d.arriba - 6, ancho - x(DIA_2026), alto - d.arriba + 6);
  ctx.restore();

  // Años
  ctx.font = `${letra}px ${FUENTES.mono}`;
  ctx.textBaseline = "alphabetic";
  [0, 365, 730, 1096, DIA_2026].forEach((dia, a) => {
    ctx.strokeStyle = c.borde;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(Math.round(x(dia)) + 0.5, d.arriba - 6);
    ctx.lineTo(Math.round(x(dia)) + 0.5, alto - 6);
    ctx.stroke();
    ctx.fillStyle = a === 4 ? c.ambar : c.tenue;
    ctx.textAlign = "left";
    ctx.fillText(String(2022 + a), x(dia) + 3, d.arriba + d.altoSerie + 14);
  });
  ctx.fillStyle = c.ambar;
  ctx.textAlign = "left";
  ctx.fillText(d.angosto ? "futuro" : "2026 · futuro", x(DIA_2026) + 3, d.arriba + 6);

  // La serie de consumo
  const minimo = Math.min(...DATOS.consumo);
  const maximo = Math.max(...DATOS.consumo);
  const y = (v) => d.arriba + 12 + (1 - (v - minimo) / (maximo - minimo)) * (d.altoSerie - 14);
  const trazo = (desde, hasta, color) => {
    ctx.beginPath();
    for (let t = desde; t < hasta; t++) {
      if (t === desde) ctx.moveTo(x(t), y(DATOS.consumo[t]));
      else ctx.lineTo(x(t), y(DATOS.consumo[t]));
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.lineJoin = "round";
    ctx.stroke();
  };
  trazo(0, DIA_2026 + 1, c.celeste);
  trazo(DIA_2026, TOTAL, c.ambar);
  ctx.fillStyle = c.tenue;
  ctx.textAlign = "right";
  ctx.fillText(String(Math.round(maximo)), d.margen - 4, y(maximo) + 3);
  ctx.fillText(String(Math.round(minimo)), d.margen - 4, y(minimo) + 3);
  ctx.textAlign = "left";
  ctx.fillStyle = c.suave;
  ctx.fillText("consumo diario (MWh)", d.margen, d.arriba - 14);

  // Leyenda
  const paleta = coloresLeyenda(c);
  d.lineas.forEach((linea, fila) => {
    for (const { texto, i, x: x0 } of linea) {
      ctx.fillStyle = paleta[i];
      ctx.fillRect(x0, d.yLeyenda + fila * 18 - 8, 11, 11);
      ctx.fillStyle = c.suave;
      ctx.textAlign = "left";
      ctx.fillText(texto, x0 + 16, d.yLeyenda + fila * 18 + 1);
    }
  });

  // Una fila por pliegue
  if (!estado?.pliegues) return;
  const colorDe = [c.borde2, c.celeste, c.ambar, c.rosa, c.violeta];
  const alfaDe = [0.35, 1, 1, 1, 1];
  estado.pliegues.forEach((pliegue, k) => {
    const y0 = d.yFilas + k * (d.filaAlto + d.separacion);
    const dias = estadosDelPliegue(pliegue);
    // Tramos de un mismo estado: pocos rectángulos en los esquemas temporales
    let inicio = 0;
    for (let t = 1; t <= n; t++) {
      if (t < n && dias[t] === dias[inicio]) continue;
      const x0 = x(descartados + inicio);
      ctx.globalAlpha = alfaDe[dias[inicio]];
      ctx.fillStyle = colorDe[dias[inicio]];
      ctx.fillRect(x0, y0, Math.max(x(descartados + t) - x0, 0.4), d.filaAlto);
      inicio = t;
    }
    ctx.globalAlpha = 1;
    ctx.fillStyle = c.tenue;
    ctx.textAlign = "right";
    ctx.fillText(String(k + 1), d.margen - 5, y0 + d.filaAlto / 2 + 3.5);
  });
}

// ── Dibujo del error de cada pliegue ─────────────────────────────────────────

const vistaBarras = lienzo(canvasBarras, {
  alto: (ancho) => (ancho < 560 ? 210 : 250),
  dibujar: (ctx, ancho, alto) => dibujarBarras(ctx, ancho, alto),
});

function dibujarBarras(ctx, ancho, alto) {
  if (!estado?.maes) return;
  const c = colores();
  const angosto = ancho < 560;
  const izq = angosto ? 30 : 40;
  const der = angosto ? 8 : 14;
  const arriba = 22;
  const abajo = 30;
  const maes = estado.maes;
  const real = DATOS.real2026;
  const tope = Math.ceil((Math.max(...maes, real, estado.estimacion) * 1.2) / 2) * 2;
  const y = (v) => arriba + (1 - v / tope) * (alto - arriba - abajo);
  const letra = angosto ? 9.5 : 10.5;

  ctx.fillStyle = c.fondo2;
  ctx.fillRect(0, 0, ancho, alto);
  ctx.font = `${letra}px ${FUENTES.mono}`;
  ctx.textBaseline = "alphabetic";

  for (const v of [0, tope / 2, tope]) {
    ctx.strokeStyle = c.borde;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(izq, Math.round(y(v)) + 0.5);
    ctx.lineTo(ancho - der, Math.round(y(v)) + 0.5);
    ctx.stroke();
    ctx.fillStyle = c.tenue;
    ctx.textAlign = "right";
    ctx.fillText(String(v), izq - 5, y(v) + 3.5);
  }
  ctx.textAlign = "left";
  ctx.fillStyle = c.suave;
  ctx.fillText("MAE de cada pliegue (MWh)", izq, 12);

  // Las barras: el MAE de cada pliegue
  const paso = (ancho - izq - der) / maes.length;
  const barra = Math.min(paso * 0.62, 56);
  maes.forEach((m, k) => {
    const cx = izq + paso * (k + 0.5);
    ctx.fillStyle = c.ambar;
    ctx.fillRect(cx - barra / 2, y(m), barra, y(0) - y(m));
    ctx.fillStyle = c.tinta;
    ctx.textAlign = "center";
    ctx.fillText(numero(m), cx, y(m) - 5);
    ctx.fillStyle = c.tenue;
    ctx.fillText(maes.length > 5 && angosto ? String(k + 1) : `k = ${k + 1}`, cx, alto - 10);
  });

  // R̂ (lo que promete) y el error real (lo que entrega). La línea más alta lleva su rótulo arriba.
  const lineas = [
    { v: estado.estimacion, color: c.turquesa, texto: `R̂ = ${numero(estado.estimacion)}`, punteada: true, lado: "left" },
    { v: real, color: c.rosa, texto: `2026 = ${numero(real)}`, punteada: false, lado: "right" },
  ];
  const masAlta = lineas[0].v >= lineas[1].v ? lineas[0] : lineas[1];
  for (const l of lineas) {
    ctx.save();
    ctx.strokeStyle = l.color;
    ctx.lineWidth = 2;
    ctx.setLineDash(l.punteada ? [6, 4] : []);
    ctx.beginPath();
    ctx.moveTo(izq, y(l.v));
    ctx.lineTo(ancho - der, y(l.v));
    ctx.stroke();
    ctx.restore();
    const dy = l === masAlta ? -10 : 12;
    rotulo(ctx, l.texto, l.lado === "left" ? izq + 6 : ancho - der - 6, y(l.v) + dy, {
      color: l.color,
      fondo: c.fondo2,
      fuente: `${letra + 1}px ${FUENTES.mono}`,
      alinear: l.lado,
    });
  }
}

// ── Textos, cifras y tabla ───────────────────────────────────────────────────

const intervalo = (dias) => {
  const primero = dias[0];
  const ultimo = dias[dias.length - 1];
  return ultimo - primero + 1 === dias.length
    ? `${fechaDelDia(primero + descartados)} → ${fechaDelDia(ultimo + descartados)}`
    : "días mezclados";
};

function llenarTabla() {
  const celda = (tr, texto, clase, dias) => {
    const td = document.createElement("td");
    if (clase) td.className = clase;
    td.textContent = texto;
    if (dias) {
      const aparte = document.createElement("div");
      aparte.className = "dias";
      aparte.textContent = `${dias} días`;
      td.append(aparte);
    }
    tr.append(td);
  };
  $("#tabla-pliegues tbody").replaceChildren(
    ...estado.pliegues.map((p, k) => {
      const tr = document.createElement("tr");
      celda(tr, String(k + 1), "k");
      celda(tr, intervalo(p.entrenamiento), "", p.entrenamiento.length);
      celda(tr, intervalo(p.prueba), "", p.prueba.length);
      celda(tr, numero(estado.maes[k], 2), "num");
      celda(tr, porcentaje(diasConFuga(p).length / p.prueba.length), "num");
      return tr;
    }),
  );
  $("#tabla-resumen").textContent = `R̂ = ${numero(estado.estimacion, 2)}`;
}

function llenarCifras() {
  const real = DATOS.real2026;
  const promete = estado.estimacion;
  $("#cifra-promete").textContent = numero(promete);
  $("#cifra-entrega").textContent = numero(real);
  $("#cifra-fuga").textContent = porcentaje(estado.fuga);
  $("#cifra-tiempo").textContent = estado.respeta ? "sí" : "no";
  const nombre = ESQUEMAS.find(([v]) => v === opciones.esquema)[1].toLowerCase();
  const cifras = `promete ${numero(promete)} MWh y el modelo entrega ${numero(real)} MWh`;
  const relativa = (real - promete) / promete;
  let cierre;
  if (Math.abs(relativa) < 0.03) cierre = "la promesa se acerca a lo que ocurre.";
  else if (relativa > 0) cierre = `el error real es <strong>${porcentaje(relativa)} mayor</strong> que el prometido.`;
  else cierre = `el error real es <strong>${porcentaje(-relativa)} menor</strong> que el prometido: el esquema es pesimista.`;
  $("#veredicto").innerHTML = `El esquema <strong>${nombre}</strong> ${cifras}: ${cierre}`;
}

function descripcion() {
  return `${estado.pliegues.length} ${estado.pliegues.length === 1 ? "pliegue" : "pliegues"}. El esquema promete ${numero(estado.estimacion)} MWh con fuga de ${porcentaje(estado.fuga)}, y el modelo entrega ${numero(DATOS.real2026)} MWh en 2026.`;
}

// ── Controles ────────────────────────────────────────────────────────────────

function montarControles() {
  const usa = USA[opciones.esquema];
  const valores = valoresDe(opciones.esquema);
  for (const p of ["K", "h", "g", "w"]) {
    const caja = $(`[data-usa="${p}"]`);
    caja.hidden = !usa.includes(p);
    if (!usa.includes(p)) continue;
    if (!valores[p].includes(opciones[p])) opciones[p] = PREDETERMINADOS[opciones.esquema][p];
    segmentado(caja.querySelector(".seg"), valores[p].map((v) => [v, String(v)]), opciones[p], (v) => {
      opciones[p] = v;
      actualizar();
    });
  }
  document.querySelectorAll("[data-esquema]").forEach((el) => {
    el.hidden = el.dataset.esquema !== opciones.esquema;
  });
}

segmentado($("#ctl-esquema"), ESQUEMAS, opciones.esquema, (v) => {
  opciones.esquema = v;
  montarControles();
  actualizar();
});

function actualizar() {
  estado = evaluar(opciones.esquema, parametrosActuales(), DATOS);
  $("#parametros-codigo").textContent = USA[opciones.esquema].map((p) => `${p} = ${opciones[p]}`).join(", ");
  const error = $("#error-sk");
  error.hidden = !estado.error;
  error.textContent = estado.error ? `ValueError: ${estado.error}` : "";
  $("#resultados").hidden = !!estado.error;
  $("#cifras").hidden = !!estado.error;
  $("#veredicto").hidden = !!estado.error;
  if (!estado.error) {
    llenarCifras();
    llenarTabla();
  }
  const detalle = estado.error ? "scikit-learn rechaza estos parámetros." : descripcion();
  canvas.setAttribute("aria-label", `La serie de consumo y una fila por pliegue de la historia. ${detalle}`);
  vistaEscena.remedir();
  vistaBarras.remedir();
}

// ── Cifras del texto: salen de los mismos datos que la página ────────────────

function llenarCifrasDelTexto() {
  for (const el of document.querySelectorAll("[data-cifra]")) {
    const [que, clave] = el.dataset.cifra.split(":");
    if (que === "real") {
      el.textContent = numero(DATOS.real2026);
      continue;
    }
    const { esquema, parametros } = desdeClave(clave);
    const r = evaluar(esquema, parametros, DATOS);
    el.textContent = que === "fuga" ? porcentaje(r.fuga) : numero(r.estimacion);
  }
  const datos = { n, historia: DATOS.meta.dias_historia, descartados };
  document.querySelectorAll("[data-dato]").forEach((el) => {
    el.textContent = String(datos[el.dataset.dato]);
  });
}

// ── Arranque ─────────────────────────────────────────────────────────────────

llenarCifrasDelTexto();
montarControles();
actualizar();
