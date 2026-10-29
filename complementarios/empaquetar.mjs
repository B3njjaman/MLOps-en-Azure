// Arma un solo script clásico por página a partir de los módulos de escenas/, logica/ y motor.js.
//
// Los módulos (import/export) son la fuente: se leen mejor y las pruebas de Node los importan.
// Pero un navegador no carga módulos desde una página abierta como archivo (file://), así que
// cada página carga su paquete de paquetes/, que funciona con y sin servidor.
//
// Uso, desde la raíz:  node complementarios/empaquetar.mjs
// La prueba pruebas/paquetes.test.js avisa si un paquete quedó viejo.

import { mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const CARPETA = dirname(fileURLToPath(import.meta.url));

/** Página → módulo de entrada. */
export const ENTRADAS = {
  portada: "escenas/portada.js",
  validacion: "escenas/validacion.js",
};

const IMPORTACION = /^import\s*\{([^}]*)\}\s*from\s*"([^"]+)";[ \t]*$/gm;
const EXPORTACION = /^export\s+(?:async\s+)?(?:function\*?|class|const|let)\s+([A-Za-z_$][\w$]*)/gm;
const NOMBRE_SUELTO = /^[A-Za-z_$][\w$]*$/;

const nombre = (ruta) => relative(CARPETA, ruta).replaceAll("\\", "/");

/**
 * El texto del paquete de una entrada. Cada módulo queda en su propia función, sin mezclar nombres.
 * Solo entiende `import { a, b } from "./x.js";` y `export function|class|const|let`. Cualquier otra
 * forma (export default, import con as, un ciclo, un nombre que el módulo no exporta) es un error
 * aquí, al armar, y no un paquete roto en el navegador.
 */
export function empaquetar(entrada) {
  const modulos = new Map();
  const enVisita = [];

  const visitar = (ruta) => {
    if (enVisita.includes(ruta)) {
      throw new Error(`importación circular: ${[...enVisita, ruta].map(nombre).join(" → ")}`);
    }
    if (modulos.has(ruta)) return;
    enVisita.push(ruta);

    const codigo = readFileSync(ruta, "utf-8").replace(/\r\n/g, "\n");
    const importaciones = [...codigo.matchAll(IMPORTACION)].map(([, nombres, desde]) => ({
      nombres: nombres.split(",").map((n) => n.trim()).filter(Boolean),
      ruta: resolve(dirname(ruta), desde),
    }));
    const exportados = [...codigo.matchAll(EXPORTACION)].map((m) => m[1]);
    const cuerpo = codigo
      .replace(IMPORTACION, "")
      .replace(EXPORTACION, (declaracion) => declaracion.replace(/^export\s+/, ""))
      .trim();

    const sobra = cuerpo.match(/^[ \t]*(import|export)\b.*$/m);
    if (sobra) throw new Error(`${nombre(ruta)}: forma no soportada por el empaquetador: ${sobra[0].trim()}`);

    for (const i of importaciones) {
      const raros = i.nombres.filter((n) => !NOMBRE_SUELTO.test(n));
      if (raros.length) throw new Error(`${nombre(ruta)}: importación no soportada: ${raros.join(", ")}`);
      visitar(i.ruta);
      const faltan = i.nombres.filter((n) => !modulos.get(i.ruta).exportados.includes(n));
      if (faltan.length) throw new Error(`${nombre(ruta)}: ${nombre(i.ruta)} no exporta ${faltan.join(", ")}`);
    }

    enVisita.pop();
    modulos.set(ruta, { ruta, cuerpo, importaciones, exportados });
  };
  visitar(resolve(CARPETA, entrada));

  const partes = [...modulos.values()].map(({ ruta, cuerpo, importaciones, exportados }) =>
    [
      `// ── ${nombre(ruta)}`,
      `modulos[${JSON.stringify(nombre(ruta))}] = (() => {`,
      ...importaciones.map((i) => `const { ${i.nombres.join(", ")} } = modulos[${JSON.stringify(nombre(i.ruta))}];`),
      cuerpo,
      `return { ${exportados.join(", ")} };`,
      "})();",
    ].join("\n"),
  );

  return [
    `// Generado por complementarios/empaquetar.mjs desde ${entrada}. No se edita a mano.`,
    "(() => {",
    '"use strict";',
    "const modulos = {};",
    "",
    partes.join("\n\n"),
    "})();",
    "",
  ].join("\n");
}

export const rutaDelPaquete = (pagina) => resolve(CARPETA, "paquetes", `${pagina}.js`);

// En Windows la letra de unidad o las mayúsculas pueden venir distintas en argv y en import.meta.url.
const mismoArchivo = (a, b) => realpathSync.native(a).toLowerCase() === realpathSync.native(b).toLowerCase();

if (process.argv[1] && mismoArchivo(process.argv[1], fileURLToPath(import.meta.url))) {
  mkdirSync(resolve(CARPETA, "paquetes"), { recursive: true });
  for (const [pagina, entrada] of Object.entries(ENTRADAS)) {
    writeFileSync(rutaDelPaquete(pagina), empaquetar(entrada));
    console.log(`paquetes/${pagina}.js ← ${entrada}`);
  }
}
