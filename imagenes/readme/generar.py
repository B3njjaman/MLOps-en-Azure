"""Genera las imágenes animadas del README, en versión clara y oscura.

    python imagenes/readme/generar.py

Solo usa la biblioteca estándar. Las animaciones son SMIL y CSS dentro de cada
SVG, sin JavaScript, para que GitHub las muestre en el README. Las fuentes son
las del sistema, porque GitHub no deja que un SVG cargue fuentes externas.
"""

from __future__ import annotations

import math
import random
from html import escape
from pathlib import Path

CARPETA = Path(__file__).parent

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

TEMAS = {
    "oscuro": {
        "fondo1": "#0b1120", "fondo2": "#141d33", "borde": "#26324a", "puntos": "#1b2640",
        "tinta": "#e6edf3", "suave": "#9aa7b8", "tenue": "#64748b",
        "nodo": "#111a2c", "pill": "#0e1626", "borde_nodo": "#34445f", "linea": "#46587a",
        "codigo": "#0a1020",
        "turquesa": "#2dd4bf", "violeta": "#a78bfa", "ambar": "#fbbf24",
        "rosa": "#fb7185", "celeste": "#38bdf8", "verde": "#4ade80",
        "brillo": 0.55, "halo": 0.14,
    },
    "claro": {
        "fondo1": "#ffffff", "fondo2": "#f1f5fa", "borde": "#d0d7de", "puntos": "#e3e9f0",
        "tinta": "#1f2328", "suave": "#57606a", "tenue": "#8c959f",
        "nodo": "#ffffff", "pill": "#f6f8fa", "borde_nodo": "#c3cdd9", "linea": "#9aa8ba",
        "codigo": "#f6f8fa",
        "turquesa": "#0d9488", "violeta": "#7c3aed", "ambar": "#d97706",
        "rosa": "#e11d48", "celeste": "#0284c7", "verde": "#16a34a",
        "brillo": 0.32, "halo": 0.08,
    },
}

# Cada módulo tiene su color, el mismo en la ruta y en su tarjeta.
ACENTOS = ["turquesa", "celeste", "violeta", "ambar", "verde", "rosa", "turquesa"]

DUR = 10  # segundos que dura un ciclo de animación
FIN = DUR - 0.8  # momento en que todo se desvanece para volver a empezar


# --- Línea de tiempo -------------------------------------------------------


def _claves(dur: float, pares: list[tuple[float, object]]) -> tuple[str, str]:
    """Convierte [(segundo, valor), ...] en keyTimes y values de SMIL."""
    pares = list(pares)
    if pares[0][0] > 0:
        pares.insert(0, (0, pares[0][1]))
    if pares[-1][0] < dur:
        pares.append((dur, pares[-1][1]))
    tiempos = ";".join(f"{min(s / dur, 1):.4f}" for s, _ in pares)
    valores = ";".join(str(v) for _, v in pares)
    return tiempos, valores


def animar(atributo: str, pares, dur: float = DUR, modo: str = "linear") -> str:
    tiempos, valores = _claves(dur, pares)
    return (
        f'<animate attributeName="{atributo}" dur="{dur}s" repeatCount="indefinite" '
        f'calcMode="{modo}" keyTimes="{tiempos}" values="{valores}"/>'
    )


def ventanas(tramos, alto: float = 1, fundido: float = 0.3) -> list[tuple[float, float]]:
    """Opacidad que sube a `alto` en cada tramo (entra, sale) y vuelve a 0."""
    pares: list[tuple[float, float]] = [(0, 0)]
    for entra, sale in tramos:
        pares += [(entra, 0), (entra + fundido, alto), (sale, alto), (sale + fundido, 0)]
    return pares


def aparecer(entra: float, sale: float = FIN, alto: float = 1) -> str:
    return animar("opacity", ventanas([(entra, sale)], alto))


class Ruta:
    """Camino de una ficha. Cada vértice queda numerado para el horario."""

    def __init__(self, x: float, y: float):
        self.d = [f"M{x:g},{y:g}"]
        self.largos = [0.0]
        self._p = (x, y)

    def a(self, x: float, y: float) -> Ruta:
        self.d.append(f"L{x:g},{y:g}")
        self._sumar(math.dist(self._p, (x, y)))
        self._p = (x, y)
        return self

    def curva(self, c1, c2, p) -> Ruta:
        p0 = self._p
        puntos = [_bezier(p0, c1, c2, p, i / 48) for i in range(49)]
        self.d.append(f"C{c1[0]:g},{c1[1]:g} {c2[0]:g},{c2[1]:g} {p[0]:g},{p[1]:g}")
        self._sumar(sum(math.dist(a, b) for a, b in zip(puntos, puntos[1:])))
        self._p = p
        return self

    def _sumar(self, largo: float) -> None:
        self.largos.append(self.largos[-1] + largo)

    def fraccion(self, vertice: int) -> float:
        return self.largos[vertice] / self.largos[-1]


def _bezier(p0, p1, p2, p3, s):
    u = 1 - s
    return tuple(u**3 * a + 3 * u * u * s * b + 3 * u * s * s * c + s**3 * d for a, b, c, d in zip(p0, p1, p2, p3))


def ficha(t: dict, color: str, ruta: Ruta, horario: list[tuple[float, int]], r: float = 7, tramos=None) -> str:
    """Un punto que recorre la ruta: horario = [(segundo, vértice), ...].

    Se dibuja debajo de los nodos, así que desaparece al entrar en uno. Si el
    camino no empieza o no termina dentro de un nodo, `tramos` dice cuándo se ve.
    """
    pares = [(s, f"{ruta.fraccion(v):.4f}") for s, v in horario]
    tiempos, puntos = _claves(DUR, pares)
    movimiento = (
        f'<animateMotion dur="{DUR}s" repeatCount="indefinite" calcMode="linear" '
        f'keyTimes="{tiempos}" keyPoints="{puntos}" path="{" ".join(ruta.d)}"/>'
    )
    opacidad = f' opacity="0">{animar("opacity", ventanas(tramos, fundido=0.1))}' if tramos else ">"
    return (
        f"<g{opacidad}{movimiento}<circle r=\"{r * 2.2:g}\" fill=\"{t[color]}\" opacity=\".45\" filter=\"url(#difuso)\"/>"
        f'<circle r="{r:g}" fill="{t[color]}"/></g>'
    )


def punta(t, x, y, desde, color) -> str:
    """Punta de flecha en (x, y), apuntando en la dirección que viene de `desde`."""
    angulo = math.atan2(y - desde[1], x - desde[0])
    vertices = [(x, y)] + [
        (x - 10 * math.cos(angulo + giro), y - 10 * math.sin(angulo + giro)) for giro in (0.45, -0.45)
    ]
    return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in vertices)}" fill="{t[color]}"/>'


# --- Piezas de dibujo ------------------------------------------------------


def ancho(texto: str, tam: float, fuente: str = "mono") -> float:
    return len(texto) * tam * (0.62 if fuente == "mono" else 0.55)


def texto(x, y, contenido, *, tam=16, color, fuente="sans", peso=400, ancla="start", extra="") -> str:
    return (
        f'<text x="{x:g}" y="{y:g}" class="{fuente}" font-size="{tam:g}" font-weight="{peso}" '
        f'fill="{color}" text-anchor="{ancla}" {extra}>{escape(contenido, quote=False)}</text>'
    )


def nodo(t, x, y, w, h, etiqueta, *, sub=None, pill=False, acento="turquesa", activo=(), tam=17) -> str:
    """Nodo centrado en (x, y). `activo` son los tramos en que se ilumina."""
    r = h / 2 if pill else 12
    x0, y0 = x - w / 2, y - h / 2
    caja = f'x="{x0:g}" y="{y0:g}" width="{w:g}" height="{h:g}" rx="{r:g}"'
    partes = []
    if activo:
        partes.append(
            f'<rect {caja} fill="{t[acento]}" opacity="0" filter="url(#difuso)">'
            f"{animar('opacity', ventanas(activo, t['brillo']))}</rect>"
        )
    partes.append(f'<rect {caja} fill="{t["pill"] if pill else t["nodo"]}" stroke="{t["borde_nodo"]}" stroke-width="1.5"/>')
    if activo:
        partes.append(
            f'<rect {caja} fill="{t[acento]}" fill-opacity=".1" stroke="{t[acento]}" stroke-width="2.5" opacity="0">'
            f"{animar('opacity', ventanas(activo))}</rect>"
        )
    centro = y - 8 if sub else y
    if etiqueta:
        partes.append(texto(x, centro, etiqueta, tam=tam, color=t["tinta"], fuente="mono", peso=600, ancla="middle", extra='dy=".35em"'))
    if sub:
        partes.append(texto(x, y + 13, sub, tam=12, color=t["suave"], fuente="mono", ancla="middle", extra='dy=".35em"'))
    return "".join(partes)


def arista(t, d, *, condicional=False, flecha=True, color="linea", ancho_linea=2) -> str:
    clase = ' class="marcha"' if condicional else ""
    punta = ' marker-end="url(#flecha)"' if flecha else ""
    return f'<path d="{d}" fill="none" stroke="{t[color]}" stroke-width="{ancho_linea}" stroke-linecap="round"{clase}{punta}/>'


def chip(t, x, y, contenido, color, *, w=None, h=30, tam=13, fuente="mono", anim="", visible=False, tinta=None) -> str:
    """Etiqueta redondeada con esquina superior izquierda en (x, y)."""
    w = w or ancho(contenido, tam, fuente) + 24
    opacidad = "" if visible else ' opacity="0"'
    return (
        f"<g{opacidad}>{anim}"
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{min(h / 2, 10):g}" fill="{t[color]}" '
        f'fill-opacity=".14" stroke="{t[color]}" stroke-opacity=".75" stroke-width="1.2"/>'
        + texto(x + w / 2, y + h / 2, contenido, tam=tam, color=tinta or t["tinta"], fuente=fuente, ancla="middle", extra='dy=".35em"')
        + "</g>"
    )


def cilindro(t, x, y_arriba, y_abajo, rx, color, activo=()) -> str:
    ry = rx * 0.2
    cuerpo = (
        f"M{x - rx:g},{y_arriba:g} L{x - rx:g},{y_abajo:g} "
        f"A{rx:g},{ry:g} 0 0 0 {x + rx:g},{y_abajo:g} L{x + rx:g},{y_arriba:g}"
    )
    partes = []
    if activo:
        partes.append(
            f'<rect x="{x - rx:g}" y="{y_arriba - ry:g}" width="{2 * rx:g}" height="{y_abajo - y_arriba + 2 * ry:g}" '
            f'rx="{ry:g}" fill="{t[color]}" opacity="0" filter="url(#difuso)">'
            f"{animar('opacity', ventanas(activo, t['brillo']))}</rect>"
        )
    partes.append(f'<path d="{cuerpo}" fill="{t["nodo"]}" stroke="{t[color]}" stroke-width="1.8"/>')
    partes.append(
        f'<ellipse cx="{x:g}" cy="{y_arriba:g}" rx="{rx:g}" ry="{ry:g}" fill="{t["pill"]}" stroke="{t[color]}" stroke-width="1.8"/>'
    )
    return "".join(partes)


def lienzo(t, w, h, titulo, cuerpo, defs="") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="titulo">
<title id="titulo">{escape(titulo, quote=False)}</title>
<style>
.sans{{font-family:{SANS}}}
.mono{{font-family:{MONO}}}
.marcha{{stroke-dasharray:6 7;animation:marcha 1.3s linear infinite}}
@keyframes marcha{{to{{stroke-dashoffset:-26}}}}
@media (prefers-reduced-motion:reduce){{.marcha{{animation:none}}}}
</style>
<defs>
<linearGradient id="fondo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t['fondo1']}"/><stop offset="1" stop-color="{t['fondo2']}"/></linearGradient>
<pattern id="puntos" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.1" fill="{t['puntos']}"/></pattern>
<filter id="difuso" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="7"/></filter>
<marker id="flecha" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,1 L9,5 L0,9 z" fill="{t['linea']}"/></marker>
{defs}
</defs>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="url(#fondo)" stroke="{t['borde']}"/>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="url(#puntos)"/>
{cuerpo}
</svg>
"""



def cadena(t, xs, y, etiquetas, *, w=112, acento, tam=13, llegadas, espera=0.6, fin_activo=True, color_ficha=None) -> list[str]:
    """Fila de nodos unidos por flechas y una ficha que los recorre.

    `llegadas[i]` es el segundo en que la ficha entra al nodo i; el nodo se
    ilumina mientras la ficha está dentro (el último, hasta el final).
    """
    partes = []
    for a, b in zip(xs, xs[1:]):
        partes.append(arista(t, f"M{a + w / 2 + 2:g},{y:g} L{b - w / 2 - 2:g},{y:g}"))
    ruta = Ruta(xs[0], y)
    for x in xs[1:]:
        ruta.a(x, y)
    horario = []
    for i, s in enumerate(llegadas):
        horario += [(s, i), (s + espera, i)]
    horario = horario[:-1]
    partes.append(ficha(t, color_ficha or acento, ruta, horario, tramos=[(llegadas[0] - 0.1, llegadas[-1] + 0.1)]))
    for i, (x, etiqueta) in enumerate(zip(xs, etiquetas)):
        ultimo = i == len(xs) - 1
        sale = FIN if (ultimo and fin_activo) else llegadas[i] + espera + 0.2
        partes.append(nodo(t, x, y, w, 44, etiqueta, acento=acento, activo=[(llegadas[i], sale)], tam=tam))
    return partes


# --- Portada ---------------------------------------------------------------


def portada(t) -> str:
    """Título y el ciclo diario: a las 06:00 corre el pipeline y al otro día llega el consumo real."""
    partes = [
        '<rect x="1" y="1" width="1198" height="418" rx="18" fill="url(#halo)"/>',
        texto(64, 84, "DATOS · MODELO · OPERACIÓN", tam=14, color=t["turquesa"], fuente="mono", peso=600, extra='letter-spacing="3"'),
        texto(60, 158, "MLOps y LLMOps", tam=56, color="url(#degradado-titulo)", peso=800, extra='letter-spacing="-1"'),
        texto(60, 222, "en Azure", tam=56, color="url(#degradado-titulo)", peso=800, extra='letter-spacing="-1"'),
        texto(64, 272, "Del notebook a producción,", tam=24, color=t["tinta"], peso=600),
        texto(64, 304, "un módulo a la vez", tam=24, color=t["suave"]),
        chip(t, 64, 346, "pronóstico diario de consumo (MWh)", "turquesa", h=30, tam=13, visible=True),
    ]

    # Reloj y pipeline de las 06:00
    partes += [
        chip(t, 604, 34, "06:00", "ambar", w=84, h=32, tam=15, visible=True),
        texto(702, 55, "cada mañana corre el pipeline", tam=13, color=t["suave"], fuente="mono"),
    ]
    xs = [650, 762, 874, 986, 1098]
    y = 116
    partes += cadena(
        t, xs, y, ["datos", "validar", "features", "modelo", "pronóstico"],
        w=92, acento="turquesa", tam=12, llegadas=[0.6, 1.3, 2.0, 2.7, 3.4], espera=0.45, color_ficha="ambar",
    )

    # Línea de consumo: historia, pronóstico (ámbar) y consumo real (verde)
    historia = [300, 276, 304, 268, 290, 252, 284, 262, 296, 258]
    puntos = [(620 + 40 * i, v) for i, v in enumerate(historia)]
    d = "M" + " L".join(f"{x},{v}" for x, v in puntos)
    xd, y_pron, y_real, base = 1020, 275, 246, 340
    partes += [
        texto(604, 196, "consumo diario (MWh)", tam=12, color=t["suave"], fuente="mono"),
        f'<path d="M604,{base} L1150,{base}" stroke="{t["borde_nodo"]}" stroke-width="2" stroke-linecap="round"/>',
        f'<path d="M{xd},200 L{xd},{base}" stroke="{t["borde_nodo"]}" stroke-width="1.6" stroke-dasharray="3 6" stroke-linecap="round"/>',
        f'<g opacity="0">{aparecer(0.2)}'
        f'<path d="{d}" fill="none" stroke="{t["celeste"]}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round" '
        f'pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">'
        + animar("stroke-dashoffset", [(0, 100), (0.3, 100), (1.8, 0), (DUR - 0.1, 0), (DUR, 100)])
        + "</path>"
        + "".join(f'<circle cx="{x}" cy="{v}" r="3.5" fill="{t["celeste"]}"/>' for x, v in puntos)
        + "</g>",
        # día que muestra el eje

        f'<g opacity="0">{aparecer(0.2, 6.0)}' + texto(xd, 362, "hoy · 06:00", tam=13, color=t["suave"], fuente="mono", ancla="middle") + "</g>",
        f'<g opacity="0">{aparecer(6.1)}' + texto(xd, 362, "día siguiente", tam=13, color=t["suave"], fuente="mono", ancla="middle") + "</g>",
        # pronóstico
        f'<g opacity="0">{aparecer(4.2)}'
        f'<path d="M{puntos[-1][0]},{puntos[-1][1]} L{xd},{y_pron}" stroke="{t["ambar"]}" stroke-width="2" stroke-dasharray="4 5" stroke-linecap="round"/>'
        f'<circle cx="{xd}" cy="{y_pron}" r="16" fill="{t["ambar"]}" opacity=".4" filter="url(#difuso)"/>'
        f'<circle cx="{xd}" cy="{y_pron}" r="8" fill="{t["ambar"]}"/></g>',
        # consumo real y error
        f'<g opacity="0">{aparecer(6.5)}'
        f'<path d="M{puntos[-1][0]},{puntos[-1][1]} L{xd},{y_real}" stroke="{t["verde"]}" stroke-width="2.4" stroke-linecap="round"/>'
        f'<circle cx="{xd}" cy="{y_real}" r="8" fill="{t["verde"]}"/></g>',
        f'<g opacity="0">{aparecer(7.2)}'
        f'<path d="M{xd},{y_pron - 11} L{xd},{y_real + 11}" stroke="{t["rosa"]}" stroke-width="3.5" stroke-linecap="round"/></g>',
        f'<g opacity="0">{aparecer(7.0)}' + arista(t, "M1034,262 L1052,270", condicional=True) + "</g>",
        nodo(t, 1102, 276, 88, 52, "monitor", sub="compara", acento="rosa", activo=[(7.0, FIN)], tam=14),
    ]
    # Leyenda
    x = 604
    for contenido, color, entra in [("pronóstico", "ambar", 4.2), ("real", "verde", 6.5), ("error del día", "rosa", 7.2)]:
        w = ancho(contenido, 12) + 22
        partes.append(chip(t, x, 382, contenido, color, w=w, h=26, tam=12, anim=aparecer(entra)))
        x += w + 10

    defs = (
        f'<linearGradient id="degradado-titulo" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{t["turquesa"]}"/><stop offset="1" stop-color="{t["violeta"]}"/></linearGradient>'
        f'<radialGradient id="halo" gradientUnits="userSpaceOnUse" cx="900" cy="200" r="480">'
        f'<stop offset="0" stop-color="{t["turquesa"]}" stop-opacity="{t["halo"] * 1.6:g}"/>'
        f'<stop offset="1" stop-color="{t["turquesa"]}" stop-opacity="0"/></radialGradient>'
    )
    return lienzo(
        t, 1200, 420,
        "MLOps y LLMOps en Azure: a las 06:00 el pipeline pronostica el consumo del día y al día siguiente el monitor compara con el consumo real",
        "\n".join(partes), defs,
    )


# --- Ruta del curso --------------------------------------------------------

MODULOS = [
    (["Del notebook al", "código reproducible"], "5 de 5 lecciones"),
    (["Experimentos y", "registro con MLflow"], "por escribir"),
    (["Pipelines de", "entrenamiento", "en Azure ML"], "por escribir"),
    (["Servir el modelo:", "online y batch"], "por escribir"),
    (["CI, CD y CT:", "lanzar sin miedo"], "por escribir"),
    (["Monitoreo", "y drift"], "por escribir"),
    (["LLMOps: agentes", "en producción"], "por escribir"),
]


def ruta_del_curso(t) -> str:
    x0, x1, y = 90, 1110, 54
    paso = (x1 - x0) / 6
    inicio, por_modulo, dur = 0.4, 1.0, 9
    partes = [
        f'<path d="M{x0},{y} L{x1},{y}" stroke="{t["borde_nodo"]}" stroke-width="4" stroke-linecap="round"/>',
        f'<path d="M{x0},{y} L{x1},{y}" stroke="url(#progreso)" stroke-width="4" stroke-linecap="round" pathLength="100" stroke-dasharray="100">'
        + animar("stroke-dashoffset", [(0, 100), (inicio, 100), (inicio + 6 * por_modulo, 0), (dur - 0.2, 0), (dur - 0.19, 100)], dur)
        + animar("opacity", [(0, 1), (dur - 0.7, 1), (dur - 0.3, 0)], dur)
        + "</path>",
    ]
    for i, (lineas, estado) in enumerate(MODULOS):
        x = x0 + i * paso
        color = t[ACENTOS[i]]
        luz = ventanas([(inicio + i * por_modulo, dur - 0.7)], fundido=0.25)
        partes += [
            f'<circle cx="{x:g}" cy="{y}" r="22" fill="{color}" opacity="0" filter="url(#difuso)">{animar("opacity", [(s, v * t["brillo"]) for s, v in luz], dur)}</circle>',
            f'<circle cx="{x:g}" cy="{y}" r="20" fill="{t["nodo"]}" stroke="{t["borde_nodo"]}" stroke-width="2.5"/>',
            f'<circle cx="{x:g}" cy="{y}" r="20" fill="{color}" fill-opacity=".16" stroke="{color}" stroke-width="2.5" opacity="0">{animar("opacity", luz, dur)}</circle>',
            texto(x, y, str(i + 1), tam=16, color=t["tinta"], fuente="mono", peso=700, ancla="middle", extra='dy=".35em"'),
        ]
        for j, linea in enumerate(lineas):
            partes.append(texto(x, 108 + 21 * j, linea, tam=15, color=t["tinta"], peso=600, ancla="middle"))
        partes.append(texto(x, 184, estado, tam=13, color=color, fuente="mono", peso=600, ancla="middle"))
    cabeza = Ruta(x0, y).a(x1, y)
    pares = [(0, "0"), (inicio, "0"), (inicio + 6 * por_modulo, "1"), (dur, "1")]
    tiempos, puntos = _claves(dur, pares)
    partes.append(
        f'<g opacity="0">{animar("opacity", [(0, 0), (inicio, 0), (inicio + 0.2, 1), (dur - 0.7, 1), (dur - 0.3, 0)], dur)}'
        f'<animateMotion dur="{dur}s" repeatCount="indefinite" calcMode="linear" keyTimes="{tiempos}" keyPoints="{puntos}" path="{" ".join(cabeza.d)}"/>'
        f'<circle r="12" fill="{t["violeta"]}" opacity=".5" filter="url(#difuso)"/><circle r="5" fill="{t["tinta"]}"/></g>'
    )
    defs = (
        f'<linearGradient id="progreso" gradientUnits="userSpaceOnUse" x1="{x0}" y1="0" x2="{x1}" y2="0">'
        f'<stop offset="0" stop-color="{t["turquesa"]}"/><stop offset="1" stop-color="{t["violeta"]}"/></linearGradient>'
    )
    return lienzo(t, 1200, 220, "Los siete módulos del curso, del 1 al 7", "\n".join(partes), defs)


# --- Tarjetas de los módulos -----------------------------------------------


def tarjeta(t, numero, titulo, lineas, cifras, diagrama, descripcion, defs="") -> str:
    clave = ACENTOS[numero - 1]
    partes = [
        texto(48, 64, f"MÓDULO {numero}", tam=15, color=t[clave], fuente="mono", peso=700, extra='letter-spacing="3"'),
        texto(46, 110, titulo, tam=34, color=t["tinta"], peso=800, extra='letter-spacing="-0.5"'),
    ]
    partes += [texto(48, 148 + 26 * i, linea, tam=18, color=t["suave"]) for i, linea in enumerate(lineas)]
    w = ancho(cifras, 14) + 28
    partes.append(chip(t, 48, 232, cifras, clave, w=w, h=32, tam=14, visible=True))
    partes.append(diagrama)
    return lienzo(t, 1200, 290, descripcion, "\n".join(partes), defs)


def modulo_1(t) -> str:
    """Tres validaciones sobre la misma línea de tiempo: aleatoria, temporal y el futuro real."""
    rng = random.Random(11)
    x0, ancho_anio, y_eje = 520, 120, 192
    partes = []
    # Bandas: 2025 como prueba temporal y 2026 como el futuro
    partes += [
        f'<rect x="{x0 + 3 * ancho_anio}" y="96" width="{ancho_anio}" height="92" rx="10" fill="{t["violeta"]}" fill-opacity=".12" stroke="{t["violeta"]}" stroke-opacity=".6" stroke-dasharray="4 5" opacity="0">{animar("opacity", ventanas([(4.5, FIN)]))}</rect>',
        f'<rect x="{x0 + 4 * ancho_anio}" y="96" width="{ancho_anio}" height="92" rx="10" fill="{t["ambar"]}" fill-opacity=".12" stroke="{t["ambar"]}" stroke-opacity=".7" stroke-dasharray="4 5" opacity="0">{animar("opacity", ventanas([(7.6, FIN)]))}</rect>',
    ]
    # Puntos: 10 por año de 2022 a 2025
    for i in range(40):
        x = x0 + 8 + i * (4 * ancho_anio - 16) / 39
        y = 142 + rng.uniform(-30, 30)
        prueba_azar = rng.random() < 0.22
        en_2025 = x >= x0 + 3 * ancho_anio
        a, b = ("violeta" if prueba_azar else "turquesa"), ("violeta" if en_2025 else "turquesa")
        pares = [(0, t[a]), (4.5, t[b]), (DUR, t[b])]
        partes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{t[a]}" opacity="0">'
            + animar("opacity", [(0, 0), (0.1 + i * 0.05, 0), (0.3 + i * 0.05, 1), (FIN, 1), (FIN + 0.3, 0)])
            + animar("fill", pares, modo="discrete")
            + "</circle>"
        )
    for i in range(8):
        x = x0 + 4 * ancho_anio + 12 + i * (ancho_anio - 24) / 7
        y = 142 + rng.uniform(-30, 30)
        partes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{t["ambar"]}" opacity="0">'
            + animar("opacity", ventanas([(7.7 + i * 0.08, FIN)]))
            + "</circle>"
        )
    # Eje con años
    partes.append(f'<path d="M{x0},{y_eje} L{x0 + 5 * ancho_anio},{y_eje}" stroke="{t["borde_nodo"]}" stroke-width="2" stroke-linecap="round"/>')
    for i, anio in enumerate(range(2022, 2027)):
        xc = x0 + i * ancho_anio + ancho_anio / 2
        partes.append(texto(xc, y_eje + 22, str(anio), tam=13, color=t["suave"], fuente="mono", ancla="middle"))
    # Títulos de cada escena
    for contenido, color, tramo in [
        ("partición aleatoria: entrenar y probar mezclados", "violeta", (0.3, 4.4)),
        ("partición temporal: entrenar hasta 2024, probar en 2025", "violeta", (4.5, 7.5)),
        ("producción: 2026 es el futuro", "ambar", (7.6, FIN)),
    ]:
        partes.append(f'<g opacity="0">{animar("opacity", ventanas([tramo]))}' + texto(x0, 72, contenido, tam=13, color=t[color], fuente="mono", peso=600) + "</g>")
    # Resultados que se acumulan
    for x, contenido, color, entra in [
        (520, "aleatoria · MAE 6,1", "violeta", 3.4),
        (720, "temporal · MAE 8,1", "violeta", 6.2),
        (920, "2026 real · MAE 9,0", "ambar", 9.0 - 0.8 - 0.1),
    ]:
        partes.append(chip(t, x, 236, contenido, color, w=184, h=32, tam=13, anim=aparecer(entra if entra < 8 else 8.0)))
    return tarjeta(
        t, 1, "La promesa y la realidad",
        ["Por qué el notebook promete más", "de lo que la planta entrega", "y cómo medirlo de verdad."],
        "5 de 5 lecciones", "\n".join(partes),
        "Módulo 1: una línea de tiempo de 2022 a 2026; la partición aleatoria promete un error de 6,1 MWh, la temporal da 8,1 y en 2026 la planta entrega 9,0",
    )


def modulo_2(t) -> str:
    """Corridas en una tabla y un registro de modelos donde el alias pasa a la versión que gana la compuerta."""
    filas = [("run-01", "0,10", "3", "9,4"), ("run-02", "0,05", "5", "8,6"), ("run-03", "0,05", "7", "8,2"), ("run-04", "0,03", "7", "8,1")]
    cols = [518, 612, 678, 772]
    partes = [
        f'<rect x="500" y="30" width="312" height="186" rx="12" fill="{t["nodo"]}" stroke="{t["borde_nodo"]}" stroke-width="1.5"/>',
        f'<path d="M500,68 L812,68" stroke="{t["borde_nodo"]}" stroke-width="1.5"/>',
    ]
    for x, h in zip(cols, ["run", "lr", "depth", "MAE"]):
        partes.append(texto(x, 54, h, tam=12, color=t["suave"], fuente="mono", peso=600))
    for i, fila in enumerate(filas):
        yc = 90 + 34 * i
        entra = 0.8 + 1.0 * i
        mejor = i == len(filas) - 1
        celdas = "".join(texto(x, yc + 1, c, tam=13, color=t["tinta"], fuente="mono", peso=600 if mejor else 400, extra='dy=".35em"') for x, c in zip(cols, fila))
        resalte = (
            f'<rect x="506" y="{yc - 15}" width="300" height="30" rx="8" fill="{t["verde"]}" fill-opacity=".16" stroke="{t["verde"]}" stroke-width="1.4" opacity="0">'
            f'{animar("opacity", ventanas([(4.6, FIN)]))}</rect>'
            if mejor else ""
        )
        partes.append(f'<g opacity="0">{aparecer(entra)}{resalte}{celdas}</g>')
    partes.append(texto(500, 244, "cada corrida guarda parámetros y MAE", tam=11, color=t["suave"], fuente="mono"))

    # Registro de modelos
    cx = [892, 992, 1092]
    partes += [
        texto(850, 50, "registro de modelos", tam=12, color=t["suave"], fuente="mono"),
        arista(t, "M816,112 L846,112", condicional=True),
    ]
    for x, etiqueta, entra in zip(cx, ["v1", "v2", "v3"], [1.6, 3.4, 5.2]):
        partes.append(f'<g opacity="0">{aparecer(entra)}' + nodo(t, x, 112, 84, 40, etiqueta, acento="celeste", activo=[(entra, entra + 0.8)] if etiqueta != "v1" else [(entra, 6.2)], tam=16) + "</g>")
    partes += [
        f'<g opacity="0">{aparecer(6.6)}' + nodo(t, 1092, 112, 84, 40, "", acento="verde", activo=[(0, FIN)]) + "</g>",
        f'<g opacity="0">{aparecer(6.6)}' + texto(1092, 112, "v3", tam=16, color=t["tinta"], fuente="mono", peso=600, ancla="middle", extra='dy=".35em"') + "</g>",
        chip(t, 962, 70, "no pasa", "rosa", w=60, h=22, tam=11, anim=aparecer(4.2)),
        chip(t, 1062, 70, "pasa", "verde", w=60, h=22, tam=11, anim=aparecer(6.0)),
        texto(850, 158, "compuerta: MAE mejor que el campeón", tam=11, color=t["suave"], fuente="mono"),
    ]
    # Alias campeón: se queda en v1 hasta que v3 gana la compuerta
    corre = (
        f'<animateTransform attributeName="transform" type="translate" dur="{DUR}s" repeatCount="indefinite" '
        f'keyTimes="0;{6.3 / DUR:.4f};{7.0 / DUR:.4f};{(DUR - 0.1) / DUR:.4f};1" values="0 0;0 0;200 0;200 0;0 0" calcMode="linear"/>'
    )
    partes.append(
        f'<g opacity="0">{aparecer(1.8)}{corre}'
        f'<path d="M892,198 L892,134" stroke="{t["ambar"]}" stroke-width="2" stroke-linecap="round" marker-end="url(#flecha)"/>'
        + chip(t, 840, 200, "campeón", "ambar", w=104, h=30, tam=14, visible=True)
        + "</g>"
    )
    partes.append(texto(850, 258, "el alias apunta al modelo que sirve", tam=11, color=t["suave"], fuente="mono"))
    return tarjeta(
        t, 2, "Experimentos con MLflow",
        ["Cada corrida con sus parámetros,", "el registro de modelos y un alias", "que apunta al campeón."],
        "por escribir", "\n".join(partes),
        "Módulo 2: las corridas de MLflow aparecen en una tabla con sus parámetros y su MAE, y el alias campeón pasa a la versión v3 que gana la compuerta",
    )


def modulo_3(t) -> str:
    """Un pipeline de components que corre paso a paso y luego se promueve de dev a test y a prod."""
    xs = [566, 698, 830, 962, 1094]
    etiquetas = ["validar", "features", "entrenar", "evaluar", "registrar"]
    llegadas = [0.4, 1.2, 2.0, 2.8, 3.6]
    partes = [texto(500, 40, "pipeline de components", tam=12, color=t["suave"], fuente="mono")]
    partes += cadena(t, xs, 84, etiquetas, w=112, acento="violeta", tam=14, llegadas=llegadas, espera=0.5)
    for x, s in zip(xs, llegadas):
        partes.append(f'<g opacity="0">{aparecer(s + 0.6)}' + texto(x, 128, "✓", tam=14, color=t["verde"], peso=700, ancla="middle") + "</g>")
    # Promoción
    centros = [690, 860, 1030]
    partes += [
        texto(500, 170, "promoción entre entornos", tam=12, color=t["suave"], fuente="mono"),
        arista(t, "M752,212 L798,212", condicional=True),
        arista(t, "M922,212 L968,212", condicional=True),
    ]
    ruta = Ruta(centros[0], 212).a(centros[1], 212).a(centros[2], 212)
    partes.append(ficha(t, "ambar", ruta, [(4.6, 0), (5.2, 0), (5.9, 1), (6.4, 1), (7.1, 2)], tramos=[(4.5, 7.2)]))
    for x, nombre, ventana in zip(centros, ["dev", "test", "prod"], [(4.6, 5.4), (5.9, 6.7), (7.1, FIN)]):
        partes.append(nodo(t, x, 212, 124, 44, nombre, pill=True, acento="violeta", activo=[ventana], tam=15))
    partes.append(texto(500, 262, "mismo código y mismas pruebas en cada paso", tam=11, color=t["suave"], fuente="mono"))
    return tarjeta(
        t, 3, "Pipelines en Azure ML",
        ["Components encadenados en un", "pipeline y la promoción de", "dev a test y a prod."],
        "por escribir", "\n".join(partes),
        "Módulo 3: un pipeline de components (validar, features, entrenar, evaluar, registrar) corre paso a paso y el modelo se promueve de dev a test y a prod",
    )


def modulo_4(t) -> str:
    """Una solicitud al endpoint online con su p95 y un batch endpoint que escribe las predicciones a las 05:30."""
    partes = [
        texto(500, 40, "online · tiempo real", tam=12, color=t["suave"], fuente="mono"),
        texto(500, 160, "batch · programado", tam=12, color=t["suave"], fuente="mono"),
        arista(t, "M624,88 L728,88"),
        arista(t, "M902,88 L1022,88"),
        arista(t, "M624,214 L728,214", condicional=True),
        arista(t, "M902,214 L1028,214"),
    ]
    online = Ruta(565, 88).a(815, 88).a(1080, 88)
    partes.append(ficha(t, "ambar", online, [(0.5, 0), (1.5, 1), (2.3, 1), (3.3, 2)], tramos=[(0.4, 3.4)]))
    batch = Ruta(565, 214).a(815, 214).a(1080, 214)
    partes.append(ficha(t, "ambar", batch, [(4.8, 0), (5.8, 1), (7.0, 1), (8.0, 2)], tramos=[(4.7, 8.1)]))
    partes += [
        nodo(t, 565, 88, 110, 40, "solicitud", pill=True, acento="ambar", activo=[(0.3, 0.9)], tam=14),
        nodo(t, 815, 88, 170, 44, "endpoint online", acento="ambar", activo=[(1.5, 2.6)], tam=14),
        nodo(t, 1080, 88, 110, 40, "respuesta", pill=True, acento="ambar", activo=[(3.3, 4.2)], tam=14),
        chip(t, 730, 26, "p95 ≈ 120 ms", "ambar", w=170, h=26, tam=13, anim=aparecer(2.6)),
        nodo(t, 565, 214, 110, 40, "05:30", pill=True, acento="ambar", activo=[(4.6, 5.4)], tam=15),
        nodo(t, 815, 214, 170, 44, "batch endpoint", acento="ambar", activo=[(5.8, 7.2)], tam=14),
        cilindro(t, 1080, 192, 236, 48, "ambar", activo=[(8.0, FIN)]),
        texto(1080, 222, "predicciones", tam=11, color=t["tinta"], fuente="mono", ancla="middle"),
        texto(1080, 266, "las del día", tam=11, color=t["suave"], fuente="mono", ancla="middle"),
    ]
    return tarjeta(
        t, 4, "Online y batch",
        ["Endpoint online para tiempo real", "y batch endpoint que deja las", "predicciones listas a las 05:30."],
        "por escribir", "\n".join(partes),
        "Módulo 4: una solicitud al endpoint online responde con su latencia p95, y a las 05:30 el batch endpoint escribe las predicciones del día",
    )


def modulo_5(t) -> str:
    """PR, tests, entrenamiento, compuerta y despliegue; el tráfico pasa de azul a verde y hay rollback."""
    xs = [566, 700, 834, 968, 1102]
    etiquetas = ["PR", "tests", "entrenar", "compuerta", "despliegue"]
    partes = cadena(t, xs, 52, etiquetas, w=112, acento="verde", tam=12, llegadas=[0.3, 0.9, 1.5, 2.2, 2.9], espera=0.4, fin_activo=False)
    # Endpoint con dos despliegues
    ey, ay, vy, bx = 176, 150, 236, 820
    dur_trafico = [(0, 6), (3.5, 6), (3.6, 4.2), (5.0, 4.2), (5.2, 2.8), (6.6, 2.8), (6.8, 0.5), (DUR - 0.1, 0.5), (DUR, 6)]
    verde_ancho = [(0, 0.1), (3.5, 0.1), (3.6, 1.2), (5.0, 1.2), (5.2, 2.8), (6.6, 2.8), (6.8, 6), (DUR - 0.1, 6), (DUR, 0.1)]
    partes += [
        texto(500, 114, "tráfico del endpoint", tam=12, color=t["suave"], fuente="mono"),
        f'<path d="M624,{ey} C690,{ey} 690,{ay} 733,{ay}" fill="none" stroke="{t["celeste"]}" stroke-linecap="round">{animar("stroke-width", dur_trafico)}</path>',
        f'<path d="M624,{ey} C690,{ey} 690,{vy} 733,{vy}" fill="none" stroke="{t["verde"]}" stroke-linecap="round" opacity="0">{animar("stroke-width", verde_ancho)}{animar("opacity", ventanas([(3.4, FIN)]))}</path>',
        nodo(t, 565, ey, 110, 44, "endpoint", acento="verde", tam=14),
        nodo(t, bx, ay, 170, 44, "azul · v1", acento="celeste", activo=[(0.2, 6.9)], tam=14),
    ]
    partes.append(f'<g opacity="0">{aparecer(3.4)}' + nodo(t, bx, vy, 170, 44, "verde · v2", acento="verde", activo=[(0, FIN)], tam=14) + "</g>")
    for yy, valores in [
        (ay, [("100 %", 0.2, 3.5), ("90 %", 3.5, 5.1), ("50 %", 5.1, 6.7), ("0 %", 6.7, FIN)]),
        (vy, [("10 %", 3.5, 5.1), ("50 %", 5.1, 6.7), ("100 %", 6.7, FIN)]),
    ]:
        for contenido, a, b in valores:
            partes.append(
                f'<g opacity="0">{animar("opacity", ventanas([(a, b)], fundido=0.15))}'
                + texto(bx + 100, yy, contenido, tam=13, color=t["tinta"], fuente="mono", peso=600, extra='dy=".35em"')
                + "</g>"
            )
    # Rollback: vuelve el tráfico al azul si el verde falla
    partes += [
        f'<path d="M{bx + 90},{vy + 14} C{bx + 200},{vy + 30} {bx + 200},{ay - 30} {bx + 90},{ay - 12}" fill="none" stroke="{t["rosa"]}" stroke-width="2" stroke-linecap="round" stroke-dasharray="6 7" marker-end="url(#flecha)" class="marcha"/>',
        texto(1088, 206, "rollback", tam=13, color=t["rosa"], fuente="mono", peso=600, ancla="middle"),
        texto(1088, 224, "si falla", tam=13, color=t["rosa"], fuente="mono", ancla="middle"),
    ]
    return tarjeta(
        t, 5, "CI, CD y CT",
        ["Tests, compuerta y despliegue", "azul y verde con tráfico gradual", "y rollback si algo falla."],
        "por escribir", "\n".join(partes),
        "Módulo 5: un pull request pasa tests, entrenamiento y compuerta; luego el tráfico del endpoint pasa de azul a verde en 90/10, 50/50 y 0/100, con rollback si falla",
    )


def modulo_6(t) -> str:
    """Dos histogramas que se separan, el PSI que cruza 0,2, la alerta y el reentrenamiento."""
    base, ancho_barra = 206, 26
    altura = lambda i: 120 * math.exp(-((i - 3.5) ** 2) / (2 * 1.5**2))
    partes = [
        chip(t, 520, 28, "entrenamiento", "turquesa", w=124, h=26, tam=12, visible=True),
        chip(t, 654, 28, "producción", "ambar", w=104, h=26, tam=12, visible=True),
        f'<path d="M514,{base} L790,{base}" stroke="{t["borde_nodo"]}" stroke-width="2" stroke-linecap="round"/>',
        texto(650, base + 24, "temperatura (feature)", tam=12, color=t["suave"], fuente="mono", ancla="middle"),
    ]
    for i in range(10):
        h = altura(i)
        partes.append(f'<rect x="{520 + 26 * i}" y="{base - h:.1f}" width="{ancho_barra - 2}" height="{h:.1f}" rx="3" fill="{t["turquesa"]}" fill-opacity=".4" stroke="{t["turquesa"]}" stroke-width="1.4"/>')
    corre = (
        f'<animateTransform attributeName="transform" type="translate" dur="{DUR}s" repeatCount="indefinite" '
        f'keyTimes="0;{1.0 / DUR:.4f};{5.2 / DUR:.4f};{8.2 / DUR:.4f};{8.8 / DUR:.4f};1" values="0 0;0 0;78 0;78 0;0 0;0 0" calcMode="linear"/>'
    )
    partes.append(f'<g opacity="0">{aparecer(0.5)}{corre}')
    for i in range(10):
        h = altura(i)
        partes.append(f'<rect x="{520 + 26 * i}" y="{base - h:.1f}" width="{ancho_barra - 2}" height="{h:.1f}" rx="3" fill="{t["ambar"]}" fill-opacity=".4" stroke="{t["ambar"]}" stroke-width="1.4"/>')
    partes.append("</g>")

    # Panel del PSI
    px, ancho_pan = 900, 240
    partes += [
        texto(px, 52, "PSI", tam=12, color=t["suave"], fuente="mono"),
        f'<rect x="{px}" y="108" width="{ancho_pan}" height="14" rx="7" fill="{t["pill"]}" stroke="{t["borde_nodo"]}" stroke-width="1.5"/>',
        f'<rect x="{px}" y="108" width="12" height="14" rx="7" fill="{t["celeste"]}">'
        + animar("width", [(0, 12), (0.6, 12), (5.2, 162), (8.2, 162), (8.8, 12), (DUR, 12)])
        + animar("fill", [(0, t["celeste"]), (3.9, t["rosa"]), (8.8, t["celeste"])], modo="discrete")
        + "</rect>",
        f'<path d="M{px + 120},98 L{px + 120},132" stroke="{t["rosa"]}" stroke-width="2.5" stroke-linecap="round"/>',
        texto(px + 120, 152, "umbral 0,2", tam=12, color=t["rosa"], fuente="mono", ancla="middle"),
    ]
    for contenido, a, b, color in [("0,02", 0.0, 2.4, "tinta"), ("0,11", 2.4, 3.9, "tinta"), ("0,27", 3.9, 8.5, "rosa"), ("0,03", 8.5, FIN, "tinta")]:
        partes.append(
            f'<g opacity="0">{animar("opacity", ventanas([(max(a, 0.05), b)], fundido=0.2))}'
            + texto(px, 92, contenido, tam=26, color=t[color], fuente="mono", peso=700)
            + "</g>"
        )
    partes += [
        chip(t, px, 176, "alerta · PSI > 0,2", "rosa", w=180, h=30, tam=13, anim=animar("opacity", ventanas([(4.2, 8.7)]))),
        chip(t, px, 218, "reentrenar el modelo", "verde", w=200, h=30, tam=13, anim=aparecer(6.2)),
    ]
    return tarjeta(
        t, 6, "Monitoreo y drift",
        ["Cuando los datos de producción", "se separan de los de entrenamiento:", "PSI, alerta y reentrenamiento."],
        "por escribir", "\n".join(partes),
        "Módulo 6: el histograma de producción se separa del de entrenamiento, el PSI cruza el umbral de 0,2, salta una alerta y el reentrenamiento vuelve a alinear los datos",
    )


def modulo_7(t) -> str:
    """Un agente detrás de un gateway: router, modelo de lenguaje y verificador, con trazas, evaluación y costo por llamada."""
    y = 104
    partes = [
        f'<rect x="590" y="40" width="562" height="140" rx="14" fill="none" stroke="{t["borde_nodo"]}" stroke-width="1.6" stroke-dasharray="3 6"/>',
        texto(606, 62, "gateway", tam=12, color=t["suave"], fuente="mono"),
        arista(t, f"M578,{y} L604,{y}"),
        arista(t, f"M737,{y} L788,{y}"),
        arista(t, f"M912,{y} L972,{y}"),
        f'<path d="M1040,{y + 26} C1040,172 850,172 850,{y + 28}" fill="none" stroke="{t["rosa"]}" stroke-width="2" stroke-linecap="round" stroke-dasharray="6 7" marker-end="url(#flecha)" class="marcha"/>',
        texto(945, 148, "si falla", tam=12, color=t["rosa"], fuente="mono", ancla="middle"),
    ]
    ruta = Ruta(540, y).a(670, y).a(850, y).a(1040, y)
    partes.append(ficha(t, "turquesa", ruta, [(0.4, 0), (1.3, 1), (1.9, 1), (2.9, 2), (4.0, 2), (5.1, 3)], tramos=[(0.3, 5.2)]))
    partes += [
        nodo(t, 540, y, 76, 36, "consulta", pill=True, activo=[(0.2, 0.9)], tam=11),
        nodo(t, 670, y, 130, 52, "router", sub="clasifica", activo=[(1.3, 2.1)], tam=16),
        nodo(t, 850, y, 124, 52, "LLM", sub="responde", activo=[(2.9, 4.2)], tam=16),
        nodo(t, 1040, y, 130, 52, "verificador", sub="revisa", activo=[(5.1, FIN)], tam=14),
    ]
    # Trazas, evaluación y costo
    partes += [
        texto(500, 208, "trazas", tam=12, color=t["suave"], fuente="mono"),
        texto(850, 208, "set de evaluación", tam=12, color=t["suave"], fuente="mono"),
        texto(1000, 208, "costo por llamada", tam=12, color=t["suave"], fuente="mono"),
    ]
    for yy, x_ini, largo, color, nombre, entra in [(218, 500, 56, "celeste", "router", 2.1), (234, 556, 150, "violeta", "llm", 4.2), (250, 706, 62, "ambar", "verif", 5.9)]:
        partes.append(
            f'<g opacity="0">{aparecer(entra)}'
            f'<rect x="{x_ini}" y="{yy}" width="{largo}" height="10" rx="5" fill="{t[color]}"/>'
            + texto(x_ini + largo + 6, yy + 9, nombre, tam=11, color=t["suave"], fuente="mono")
            + "</g>"
        )
    for i in range(5):
        partes.append(
            f'<circle cx="{858 + 28 * i}" cy="236" r="8" fill="{t["pill"]}" stroke="{t["borde_nodo"]}" stroke-width="1.5"/>'
            f'<g opacity="0">{aparecer(6.0 + 0.35 * i)}<circle cx="{858 + 28 * i}" cy="236" r="8" fill="{t["verde"]}" fill-opacity=".25" stroke="{t["verde"]}" stroke-width="2"/>'
            + texto(858 + 28 * i, 236, "✓", tam=10, color=t["verde"], peso=700, ancla="middle", extra='dy=".35em"')
            + "</g>"
        )
    partes += [
        chip(t, 1000, 220, "820 + 140 tokens", "turquesa", w=150, h=30, tam=13, anim=aparecer(5.4)),
        texto(1000, 268, "entrada + salida", tam=11, color=t["suave"], fuente="mono"),
    ]
    return tarjeta(
        t, 7, "LLMOps en producción",
        ["Un agente de LangGraph detrás de", "un gateway, con trazas, evaluación", "y costo por llamada."],
        "por escribir", "\n".join(p for p in partes if p),
        "Módulo 7: la consulta a un agente pasa por un router que la clasifica, un LLM y un verificador detrás de un gateway, con trazas, set de evaluación y costo por llamada en tokens",
    )


PIEZAS = {
    "portada": portada,
    "ruta": ruta_del_curso,
    **{f"modulo-{i}": f for i, f in enumerate([modulo_1, modulo_2, modulo_3, modulo_4, modulo_5, modulo_6, modulo_7], start=1)},
}


def main() -> None:
    for nombre, dibujar in PIEZAS.items():
        for tema, colores in TEMAS.items():
            archivo = CARPETA / f"{nombre}-{tema}.svg"
            archivo.write_text(dibujar(colores), encoding="utf-8")
            print(archivo.relative_to(CARPETA.parent.parent))


if __name__ == "__main__":
    main()
