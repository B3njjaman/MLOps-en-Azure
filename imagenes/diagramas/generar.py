"""Genera los diagramas del curso con D2 (https://d2lang.com).

Cada archivo `fuentes/<carpeta>/<nombre>.d2` se convierte en `<carpeta>/<nombre>.svg`.
Si la fuente tiene `steps`, el SVG es animado y recorre los pasos uno tras otro.

Los diagramas usan colores de marcador (definidos en `fuentes/estilo.d2`). Este
script los cambia por CSS con la paleta de abajo, en versión clara y oscura, así
cada SVG sigue el tema del navegador.

Uso, desde cualquier carpeta:

    python imagenes/diagramas/generar.py            # todos
    python imagenes/diagramas/generar.py agente     # solo los que contienen "agente" en la ruta
    python imagenes/diagramas/generar.py agente --vista <carpeta>   # PNG de cada paso, para revisar

Necesita D2 0.9 o más nuevo. Lo busca en la variable de entorno D2, en el PATH
y en la carpeta donde lo deja la versión portable para Windows.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CARPETA = Path(__file__).parent
FUENTES = CARPETA / "fuentes"
ESTILO = FUENTES / "estilo.d2"

INTERVALO_MS = 1600  # cuánto dura cada paso de una animación, salvo que la fuente diga otra cosa

# Paleta: (modo claro, modo oscuro). Es la misma de las imágenes del README.
PALETA = {
    "fondo": ("#ffffff", "#0b1120"),
    "tarjeta": ("#f6f8fa", "#111a2c"),
    "borde": ("#d0d7de", "#26324a"),
    "tinta": ("#1f2328", "#e6edf3"),
    "suave": ("#57606a", "#9aa7b8"),
    "tenue": ("#8c959f", "#64748b"),
    "nodo": ("#ffffff", "#0e1626"),
    "borde-nodo": ("#aab6c5", "#3b4d6b"),
    "linea": ("#8c9bb0", "#52668a"),
    "turquesa": ("#0d9488", "#2dd4bf"),
    "turquesa-suave": ("#ccfbf1", "#0f3a3a"),
    "violeta": ("#7c3aed", "#a78bfa"),
    "violeta-suave": ("#ede9fe", "#2a2152"),
    "ambar": ("#d97706", "#fbbf24"),
    "ambar-suave": ("#fef3c7", "#3a2d0d"),
    "rosa": ("#e11d48", "#fb7185"),
    "rosa-suave": ("#ffe4e6", "#43192b"),
    "celeste": ("#0284c7", "#38bdf8"),
    "celeste-suave": ("#e0f2fe", "#0c2e48"),
    "verde": ("#16a34a", "#4ade80"),
    "verde-suave": ("#dcfce7", "#0f3220"),
}

# Colores del tema de D2 que aparecen en piezas que no se pueden estilar desde el
# código (el fondo de las etiquetas de las aristas, por ejemplo). Se fuerzan a la paleta.
TEMA_D2 = {
    "N1": "tinta",
    "N2": "suave",
    "N7": "fondo",
}


def buscar_d2():
    candidatos = [os.environ.get("D2"), shutil.which("d2")]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidatos += sorted(Path(local, "Programs", "d2").glob("d2-*/bin/d2.exe"), reverse=True)
    for candidato in candidatos:
        if candidato and Path(candidato).exists():
            return str(candidato)
    sys.exit("No encontré D2. Instálalo (https://d2lang.com/tour/install) o indica su ruta en la variable D2.")


def marcadores():
    """Lee de estilo.d2 qué color de marcador corresponde a cada nombre de la paleta."""
    texto = ESTILO.read_text(encoding="utf-8")
    encontrados = dict(re.findall(r'^\s*([a-z-]+):\s*"(#0a0[bc]\d\d)"', texto, flags=re.M))
    faltan = set(PALETA) - set(encontrados)
    sobran = set(encontrados) - set(PALETA)
    if faltan or sobran:
        sys.exit(f"estilo.d2 y PALETA no coinciden. Faltan en estilo.d2: {faltan}. Sobran: {sobran}.")
    return encontrados


def css_de_colores(nombre_a_marcador):
    def reglas(indice):
        lineas = []
        for nombre, marcador in nombre_a_marcador.items():
            color = PALETA[nombre][indice]
            for propiedad in ("fill", "stroke"):
                lineas.append(f'[{propiedad}="{marcador}" i]{{{propiedad}:{color} !important}}')
        for codigo, nombre in TEMA_D2.items():
            color = PALETA[nombre][indice]
            lineas.append(f".fill-{codigo}{{fill:{color} !important}}")
            lineas.append(f".stroke-{codigo}{{stroke:{color} !important}}")
            lineas.append(f".color-{codigo}{{color:{color} !important}}")
        return "\n".join(lineas)

    return (
        "<style>\n"
        + reglas(0)
        + "\n@media (prefers-color-scheme: dark) {\n"
        + reglas(1)
        + "\n}\n</style>"
    )


def intervalo_de(texto):
    """Una fuente puede pedir otro intervalo con una línea `# intervalo: 2000`."""
    coincidencia = re.search(r"^#\s*intervalo:\s*(\d+)", texto, flags=re.M)
    return int(coincidencia.group(1)) if coincidencia else INTERVALO_MS


def generar(d2, fuente, css):
    relativa = fuente.relative_to(FUENTES).with_suffix(".svg")
    destino = CARPETA / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = fuente.read_text(encoding="utf-8")
    comando = [d2, "--scale=1", "--no-xml-tag", f"--salt={relativa.stem}"]
    if re.search(r"^steps\s*:", texto, flags=re.M):
        comando.append(f"--animate-interval={intervalo_de(texto)}")
    # D2 resuelve `...@../estilo` desde la carpeta en que corre, así que corre en la de la fuente.
    comando += [fuente.name, str(destino.resolve())]
    resultado = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", cwd=fuente.parent)
    if resultado.returncode != 0:
        print(f"ERROR  {relativa}\n{resultado.stderr.strip()}")
        return False
    svg = destino.read_text(encoding="utf-8")
    # El estilo va justo después de la etiqueta <svg ...> de afuera.
    svg = re.sub(r"(<svg\b[^>]*>)", lambda m: m.group(1) + css, svg, count=1)
    destino.write_text(svg, encoding="utf-8")
    print(f"listo  {relativa}  ({len(svg) // 1024} KB)")
    return True


def vista_previa(d2, fuentes, carpeta, nombre_a_marcador):
    """Guarda un PNG por paso de cada diagrama, en modo claro y oscuro, para revisarlos sin navegador.

    Copia las fuentes a `carpeta` con los marcadores ya cambiados por los colores reales.
    """
    for indice, modo in enumerate(("claro", "oscuro")):
        copia = Path(carpeta) / "fuentes" / modo
        if copia.exists():
            shutil.rmtree(copia)
        shutil.copytree(FUENTES, copia)
        estilo = (copia / "estilo.d2").read_text(encoding="utf-8")
        for nombre, marcador in nombre_a_marcador.items():
            estilo = estilo.replace(f'"{marcador}"', f'"{PALETA[nombre][indice]}"')
        (copia / "estilo.d2").write_text(estilo, encoding="utf-8")
        for fuente in fuentes:
            relativa = fuente.relative_to(FUENTES)
            destino = (Path(carpeta) / modo / relativa.with_suffix(".png")).resolve()
            destino.parent.mkdir(parents=True, exist_ok=True)
            resultado = subprocess.run(
                [d2, "--scale=1", relativa.name, str(destino)],
                capture_output=True, text=True, encoding="utf-8", cwd=copia / relativa.parent,
            )
            estado = "listo " if resultado.returncode == 0 else "ERROR "
            print(f"{estado} {modo}/{relativa.with_suffix('')}" + ("" if resultado.returncode == 0 else f"\n{resultado.stderr.strip()}"))
    print(f"\nLos diagramas con pasos quedan como una carpeta con un PNG por paso (index.png es el primero) en {carpeta}")


def main():
    argumentos = sys.argv[1:]
    carpeta_vista = None
    if "--vista" in argumentos:
        posicion = argumentos.index("--vista")
        carpeta_vista = argumentos[posicion + 1]
        del argumentos[posicion : posicion + 2]
    filtro = argumentos[0] if argumentos else ""
    d2 = buscar_d2()
    nombre_a_marcador = marcadores()
    fuentes = [f for f in sorted(FUENTES.rglob("*.d2")) if f != ESTILO and filtro in f.as_posix()]
    if not fuentes:
        sys.exit(f"No hay fuentes que coincidan con '{filtro}'.")
    if carpeta_vista:
        vista_previa(d2, fuentes, carpeta_vista, nombre_a_marcador)
        return
    css = css_de_colores(nombre_a_marcador)
    errores = sum(not generar(d2, f, css) for f in fuentes)
    if errores:
        sys.exit(f"{errores} diagramas con errores.")


if __name__ == "__main__":
    main()
