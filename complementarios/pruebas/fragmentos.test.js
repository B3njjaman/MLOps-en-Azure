// El código que muestran las páginas tiene que estar, tal cual, en el archivo que citan
// (data-fuente). Así, si cambia la lección o la lógica, la prueba avisa que la página quedó vieja.
// Se compara línea a línea sin la sangría, porque un fragmento puede venir de dentro de una función.

import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";

const raiz = new URL("../../", import.meta.url);
const carpeta = new URL("../", import.meta.url);

const entidades = { "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&amp;": "&" };
const desescapar = (t) => t.replace(/&(lt|gt|quot|#39|amp);/g, (m) => entidades[m]);
const sinSangria = (t) => t.split("\n").map((l) => l.trim()).join("\n");

function textoDe(ruta) {
  const crudo = readFileSync(new URL(ruta, raiz), "utf-8");
  if (!ruta.endsWith(".ipynb")) return crudo;
  const nb = JSON.parse(crudo);
  return nb.cells.filter((c) => c.cell_type === "code").map((c) => [].concat(c.source).join("")).join("\n\n");
}

const paginas = readdirSync(carpeta).filter((f) => f.endsWith(".html"));

for (const pagina of paginas) {
  const html = readFileSync(new URL(pagina, carpeta), "utf-8");
  const fragmentos = [...html.matchAll(/<pre class="code" data-fuente="([^"]+)"><code>([\s\S]*?)<\/code><\/pre>/g)];
  if (fragmentos.length === 0) continue;
  test(`${pagina}: el código mostrado está en su fuente`, () => {
    for (const [, fuente, codigo] of fragmentos) {
      const fragmento = sinSangria(desescapar(codigo));
      assert.ok(sinSangria(textoDe(fuente)).includes(fragmento), `no está en ${fuente}:\n${fragmento}`);
    }
  });
}

test("toda página con código lo cita con data-fuente", () => {
  for (const pagina of paginas) {
    const html = readFileSync(new URL(pagina, carpeta), "utf-8");
    const sinFuente = [...html.matchAll(/<pre class="code"(?! data-fuente=)/g)];
    assert.equal(sinFuente.length, 0, `${pagina} tiene bloques de código sin data-fuente`);
  }
});
