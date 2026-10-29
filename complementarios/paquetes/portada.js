// Generado por complementarios/empaquetar.mjs desde escenas/portada.js. No se edita a mano.
(() => {
"use strict";
const modulos = {};

// ── motor.js
modulos["motor.js"] = (() => {
// Motor común de las simulaciones: modo claro u oscuro, canvas nítido, controles,
// botones de copiar, fórmulas con KaTeX y ayudas de dibujo. Cada simulación trae su
// propia escena y su lógica (en logica/), así que cambiar una no afecta a las demás.

const CLAVE_MODO = "complementarios-modo";

const movimientoReducido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** El modo en uso: el elegido con el botón o, si no hay, el del sistema. */
function modoActual() {
  const elegido = document.documentElement.dataset.modo;
  if (elegido === "claro" || elegido === "oscuro") return elegido;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro";
}

const avisos = new Set();

/** Llama a `fn` cada vez que cambia el modo, para redibujar el canvas con los colores nuevos. */
function alCambiarModo(fn) {
  avisos.add(fn);
}

function avisarModo() {
  for (const fn of avisos) fn();
}

/** Los colores de estilo.css, leídos en el modo actual. */
function colores() {
  const css = getComputedStyle(document.documentElement);
  const nombres = [
    "fondo", "fondo-2", "tarjeta", "borde", "borde-2", "tinta", "suave", "tenue", "nodo", "linea",
    "turquesa", "turquesa-suave", "violeta", "violeta-suave", "ambar", "ambar-suave",
    "rosa", "rosa-suave", "celeste", "celeste-suave", "verde", "verde-suave",
  ];
  const c = {};
  for (const n of nombres) c[n.replace(/-(\w)/g, (_, l) => l.toUpperCase())] = css.getPropertyValue(`--${n}`).trim();
  return c;
}

const FUENTES = {
  mono: '"IBM Plex Mono", ui-monospace, monospace',
  sans: '"IBM Plex Sans", system-ui, sans-serif',
  serif: '"Fraunces", Georgia, serif',
};

function iniciarModo() {
  const boton = document.querySelector(".modo");
  const rotular = () => {
    if (boton) boton.textContent = modoActual() === "oscuro" ? "Modo claro" : "Modo oscuro";
  };
  rotular();
  boton?.addEventListener("click", () => {
    const nuevo = modoActual() === "oscuro" ? "claro" : "oscuro";
    document.documentElement.dataset.modo = nuevo;
    try {
      localStorage.setItem(CLAVE_MODO, nuevo);
    } catch {
      /* sin almacenamiento, el modo dura hasta recargar */
    }
    rotular();
    avisarModo();
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    rotular();
    avisarModo();
  });
}

/** Los bloques aparecen al entrar en pantalla. Sin JS o con movimiento reducido, se ven de inmediato. */
function iniciarBloques() {
  const bloques = document.querySelectorAll(".blk");
  if (movimientoReducido() || !("IntersectionObserver" in window)) {
    bloques.forEach((b) => b.classList.add("in"));
    return;
  }
  const obs = new IntersectionObserver(
    (entradas) => {
      for (const e of entradas) {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          obs.unobserve(e.target);
        }
      }
    },
    { rootMargin: "0px 0px -8% 0px" },
  );
  bloques.forEach((b) => obs.observe(b));
}

/** Cada bloque de código tiene su botón, en la línea que dice el lenguaje y el archivo. */
function iniciarCopiar() {
  for (const boton of document.querySelectorAll(".lang .copy")) {
    const rotulo = boton.closest(".lang");
    boton.setAttribute("aria-label", `Copiar: ${rotulo.querySelector("span")?.textContent ?? "código"}`);
    boton.addEventListener("click", async () => {
      const codigo = rotulo.nextElementSibling.querySelector("code").textContent;
      try {
        await navigator.clipboard.writeText(codigo);
        boton.textContent = "Copiado";
        boton.classList.add("done");
        setTimeout(() => {
          boton.textContent = "Copiar";
          boton.classList.remove("done");
        }, 1600);
      } catch {
        boton.textContent = "No se pudo";
      }
    });
  }
}

/** Las fórmulas van en elementos con clase `tex` (en línea) o `tex-d` (aparte). */
function iniciarFormulas() {
  const dibujar = () => {
    if (!window.katex) return false;
    for (const el of document.querySelectorAll(".tex, .tex-d")) {
      window.katex.render(el.textContent, el, { displayMode: el.classList.contains("tex-d"), throwOnError: false });
    }
    return true;
  };
  if (!dibujar()) window.addEventListener("load", dibujar, { once: true });
}

/** Arranca lo común de la página. Llamarlo una vez, desde el módulo de la simulación. */
function iniciarPagina() {
  document.documentElement.classList.add("js");
  iniciarModo();
  iniciarBloques();
  iniciarCopiar();
  iniciarFormulas();
}

/**
 * Prepara un canvas nítido en pantallas de alta densidad. `alto(ancho)` da el alto en px CSS
 * para el ancho disponible; `dibujar(ctx, ancho, alto)` pinta la escena. Devuelve `redibujar` y `remedir`.
 */
function lienzo(canvas, { alto, dibujar }) {
  const ctx = canvas.getContext("2d");
  let ancho = 0;
  let h = 0;
  const medir = () => {
    ancho = canvas.parentElement.clientWidth;
    h = Math.round(alto(ancho));
    const dpr = Math.min(window.devicePixelRatio || 1, 3);
    canvas.width = Math.round(ancho * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.height = `${h}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  const redibujar = () => {
    if (!ancho) medir();
    ctx.clearRect(0, 0, ancho, h);
    dibujar(ctx, ancho, h);
  };
  new ResizeObserver(() => {
    medir();
    redibujar();
  }).observe(canvas.parentElement);
  alCambiarModo(redibujar);
  document.fonts?.ready.then(redibujar);
  // Si el alto depende de lo que se dibuja (más o menos filas), remedir lo recalcula.
  const remedir = () => {
    medir();
    redibujar();
  };
  return { redibujar, remedir, ancho: () => ancho };
}

/** Un grupo de botones donde se elige una opción. `opciones` = [[valor, rótulo], …]. */
function segmentado(contenedor, opciones, valor, alCambiar) {
  contenedor.replaceChildren();
  const botones = opciones.map(([v, rotulo]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = rotulo;
    b.setAttribute("aria-pressed", String(v === valor));
    b.addEventListener("click", () => {
      botones.forEach((o) => o.setAttribute("aria-pressed", String(o === b)));
      alCambiar(v);
    });
    contenedor.append(b);
    return b;
  });
}

/** Un deslizador con su valor a la vista. `formato(v)` da el texto del valor. */
function deslizador(input, salida, formato, alCambiar) {
  const mostrar = () => {
    salida.textContent = formato(Number(input.value));
  };
  input.addEventListener("input", () => {
    mostrar();
    alCambiar(Number(input.value));
  });
  mostrar();
}

// ── Ayudas de dibujo ────────────────────────────────────────────────────────

function cajaRedonda(ctx, x, y, w, h, r) {
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(x, y, w, h, r);
    return;
  }
  // Safari anterior a 16 no tiene roundRect.
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** Punto y tangente de la curva cuadrática p0 → p2 con control p1, en t ∈ [0, 1]. */
function enCurva(p0, p1, p2, t) {
  const u = 1 - t;
  return {
    x: u * u * p0.x + 2 * u * t * p1.x + t * t * p2.x,
    y: u * u * p0.y + 2 * u * t * p1.y + t * t * p2.y,
    dx: 2 * u * (p1.x - p0.x) + 2 * t * (p2.x - p1.x),
    dy: 2 * u * (p1.y - p0.y) + 2 * t * (p2.y - p1.y),
  };
}

/** Flecha curva de p0 a p2 con control p1. */
function flecha(ctx, p0, p1, p2, { color, ancho = 1.5, punteada = false, punta = 7 }) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = ancho;
  ctx.setLineDash(punteada ? [5, 5] : []);
  ctx.beginPath();
  ctx.moveTo(p0.x, p0.y);
  ctx.quadraticCurveTo(p1.x, p1.y, p2.x, p2.y);
  ctx.stroke();
  ctx.setLineDash([]);
  const { dx, dy } = enCurva(p0, p1, p2, 1);
  const ang = Math.atan2(dy, dx);
  ctx.beginPath();
  ctx.moveTo(p2.x, p2.y);
  ctx.lineTo(p2.x - punta * Math.cos(ang - 0.42), p2.y - punta * Math.sin(ang - 0.42));
  ctx.lineTo(p2.x - punta * Math.cos(ang + 0.42), p2.y - punta * Math.sin(ang + 0.42));
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

/** Texto con fondo, para rotular una arista sin que la línea lo tape. */
function rotulo(ctx, texto, x, y, { color, fondo, fuente, alinear = "center" }) {
  ctx.save();
  ctx.font = fuente;
  const w = ctx.measureText(texto).width;
  const h = parseFloat(fuente) * 1.35;
  const x0 = alinear === "center" ? x - w / 2 : alinear === "right" ? x - w : x;
  ctx.fillStyle = fondo;
  ctx.fillRect(x0 - 4, y - h / 2, w + 8, h);
  ctx.fillStyle = color;
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  ctx.fillText(texto, x0, y + 0.5);
  ctx.restore();
}

/** Reloj de animación: llama a `cuadro(t)` con t de 0 a 1 durante `ms`, y después a `fin`. */
function animar(ms, cuadro, fin) {
  if (movimientoReducido()) {
    cuadro(1);
    fin?.();
    return () => {};
  }
  let vivo = true;
  const t0 = performance.now();
  const tick = (ahora) => {
    if (!vivo) return;
    const t = Math.min(1, (ahora - t0) / ms);
    cuadro(t);
    if (t < 1) requestAnimationFrame(tick);
    else fin?.();
  };
  requestAnimationFrame(tick);
  return () => {
    vivo = false;
  };
}

const suavizar = (t) => 1 - Math.pow(1 - t, 3);
return { movimientoReducido, modoActual, alCambiarModo, colores, FUENTES, iniciarPagina, lienzo, segmentado, deslizador, cajaRedonda, enCurva, flecha, rotulo, animar, suavizar };
})();

// ── escenas/portada.js
modulos["escenas/portada.js"] = (() => {
const { iniciarPagina } = modulos["motor.js"];
// Portada de Complementarios: solo lo común a todas las páginas (modo claro u oscuro y bloques).



iniciarPagina();
return {  };
})();
})();
