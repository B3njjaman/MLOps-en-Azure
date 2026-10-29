// Los paquetes de paquetes/ tienen que coincidir con los módulos de los que salen, compilar como
// script clásico y ser lo que carga cada página: un módulo no carga si la página se abre como archivo.

import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import vm from "node:vm";

import { ENTRADAS, empaquetar, rutaDelPaquete } from "../empaquetar.mjs";

const leer = (ruta) => readFileSync(ruta, "utf-8").replace(/\r\n/g, "\n");

for (const [pagina, entrada] of Object.entries(ENTRADAS)) {
  test(`paquetes/${pagina}.js está al día con ${entrada} y compila`, () => {
    const texto = leer(rutaDelPaquete(pagina));
    assert.equal(texto, empaquetar(entrada), "correr: node complementarios/empaquetar.mjs");
    assert.doesNotThrow(() => new vm.Script(texto, { filename: `paquetes/${pagina}.js` }));
  });
}

test("las páginas cargan su paquete y ningún módulo", () => {
  const paginas = { "index.html": "portada", "validacion.html": "validacion" };
  for (const [html, pagina] of Object.entries(paginas)) {
    const texto = leer(new URL(`../${html}`, import.meta.url));
    assert.ok(texto.includes(`<script defer src="paquetes/${pagina}.js"></script>`), `${html} no carga paquetes/${pagina}.js`);
    assert.ok(!texto.includes('type="module"'), `${html} todavía carga un módulo`);
  }
});

test("el empaquetador rechaza lo que no sabe traducir", () => {
  const carpeta = mkdtempSync(join(tmpdir(), "empaquetar-"));
  const casos = {
    "export default": [{ "a.js": "export default function f() {}\n" }, /forma no soportada/],
    "import con as": [{ "a.js": 'import { x as y } from "./b.js";\n', "b.js": "export const x = 1;\n" }, /no soportada/],
    "nombre que no se exporta": [{ "a.js": 'import { z } from "./b.js";\n', "b.js": "export const x = 1;\n" }, /no exporta z/],
    "ciclo": [{ "a.js": 'import { y } from "./b.js";\nexport const x = 1;\n', "b.js": 'import { x } from "./a.js";\nexport const y = 2;\n' }, /circular/],
  };
  try {
    for (const [caso, [archivos, error]] of Object.entries(casos)) {
      const sub = mkdtempSync(join(carpeta, "caso-"));
      for (const [archivo, codigo] of Object.entries(archivos)) writeFileSync(join(sub, archivo), codigo);
      assert.throws(() => empaquetar(join(sub, "a.js")), error, caso);
    }
  } finally {
    rmSync(carpeta, { recursive: true, force: true });
  }
});
