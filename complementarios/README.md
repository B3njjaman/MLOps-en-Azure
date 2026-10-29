# Complementarios

Simulaciones interactivas del curso: las ideas que se entienden mejor viéndolas correr. Cada una sigue una lección, con la matemática y el código al lado. Los errores salen del modelo real de la planta y su lógica está probada contra scikit-learn.

**Para abrirlas:** [b3njjaman.github.io/MLOps-en-Azure/complementarios](https://b3njjaman.github.io/MLOps-en-Azure/complementarios/). Con el repositorio en el PC, también basta abrir `complementarios/index.html` en el navegador, sin servidor. GitHub muestra los archivos de esta carpeta, pero no ejecuta las páginas.

| Simulación | Lección | Qué se ve |
|---|---|---|
| [Validación temporal](https://b3njjaman.github.io/MLOps-en-Azure/complementarios/validacion.html) | Módulo 1, lección 3 | Por qué partir la serie al azar promete menos error del que el modelo entrega en 2026, y cómo lo corrigen el holdout, el origen móvil y la ventana deslizante, con la fuga a la vista |
| Drift y PSI<br><sub>próximamente</sub> | Módulo 6 | Una variable que se corre de la distribución de entrenamiento y el índice que lo mide |
| Despliegue canary<br><sub>próximamente</sub> | Módulo 5 | Una versión nueva con una fracción del tráfico y la métrica que decide si sube o se revierte |

## Cómo está hecho

```
complementarios/
├── index.html, validacion.html   las páginas
├── estilo.css, motor.js          lo común: paleta del curso, modo claro u oscuro, canvas, KaTeX
├── logica/                       los esquemas de validación en JavaScript, sin dibujo
├── escenas/                      el dibujo y los controles de cada página
├── datos/                        los errores precalculados con el modelo real (generado)
├── paquetes/                     lo que carga el navegador: un script por página (generado)
└── pruebas/                      casos de scikit-learn y las pruebas de Node
```

`logica/`, `escenas/`, `datos/validacion.js` y `motor.js` son módulos de JavaScript. Un navegador no carga módulos en una página abierta como archivo, así que cada página carga su paquete de `paquetes/`, armado desde esos módulos. Desde la raíz del repositorio:

```bash
node complementarios/empaquetar.mjs                  # rearma paquetes/
node --test "complementarios/pruebas/*.test.js"      # Node 22 o más nuevo
python complementarios/datos/generar_datos.py        # solo si cambia el modelo o la planta; ~10 min
python complementarios/pruebas/generar_casos.py      # solo si cambian los casos; ~20 s
```

Los scripts de Python necesitan scikit-learn, pandas y numpy.

### Validación temporal: la rejilla precalculada

`datos/generar_datos.py` entrena el `RandomForestRegressor` de la lección una vez por pliegue de cada configuración: 111 configuraciones, 558 entrenamientos, sobre las 1454 filas de la historia con rezagos completos. La asignación de `KFold` con mezcla también viene de Python, porque el generador de numpy no se replica en JavaScript.

| Esquema | Parámetros |
|---|---|
| Aleatorio | K en 3, 5, 10 |
| Holdout temporal | h en 30, 90, 180, 365; g en 0, 7, 30 |
| Origen móvil (ventana creciente) | K en 3, 5, 10; h en 30, 90, 180; g en 0, 7, 30 |
| Ventana deslizante | lo mismo, con w en 180, 365, 730 |

Las combinaciones que scikit-learn rechaza (K·h + g ≥ n) no se entrenan: la página muestra su `ValueError`. El error real en 2026 (modelo entrenado con toda la historia) se guarda junto a la rejilla.

Las pruebas exigen cuatro cosas: que los pliegues de `TimeSeriesSplit`, del holdout y de `KFold` y su fuga coincidan con scikit-learn en miles de combinaciones de n, K, h, g y w (errores incluidos); que los MAE precalculados sean los de un reentrenamiento hecho aparte y que su promedio sea el R̂ de la página; que el código mostrado en cada página esté tal cual en el archivo que cita, y que los paquetes estén al día con sus módulos.
