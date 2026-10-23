# Carga de evaluaciones desde un archivo

Cada evaluación se incorpora **como datos**, sin tocar el motor: se
describe en un archivo JSON (`database/contenido/<nombre>.json`) y se
carga con un solo comando. El archivo de la Prueba de Moss
(`database/contenido/moss.json`) es el primer ejemplo y sirve de modelo.

```bash
# 1. validar el archivo (no toca la base de datos)
python3 scripts/cargar_prueba.py database/contenido/moss.json --validar

# 2. cargarlo (requiere migraciones y catálogos sembrados: docs/INSTALACION.md)
python3 scripts/cargar_prueba.py database/contenido/moss.json

# 3. si la evaluación ya existe y quieres cargar contenido nuevo/corregido
#    como una NUEVA VERSIÓN (la anterior queda archivada, no se borra)
python3 scripts/cargar_prueba.py database/contenido/moss.json --version-nueva
```

La carga es **todo o nada**: si algo falla a mitad, no queda una
evaluación a medias. Cargar dos veces la misma evaluación sin
`--version-nueva` se rechaza (no se duplica nada).

## Formato

```jsonc
{
  "categoria": {"codigo": "HABILIDADES_OTROS", "nombre": "Habilidades / Otros"},
  "prueba": {
    "codigo": "MOSS", "nombre": "Prueba de Moss",
    "descripcion": "...",            // opcional
    "instrucciones": "...",          // opcional: lo que ve el evaluado antes de empezar
    "tiempo_limite_minutos": 30,     // opcional (omitido = sin límite)
    "intentos_permitidos": 1         // opcional (por defecto 1)
  },
  "notas_version": "...",            // opcional
  "preguntas": [
    {
      "orden": 1,
      "tipo": "OPCION_UNICA",        // opcional; por defecto OPCION_UNICA
      "enunciado": "...",
      "configuracion": {"factor_codigo": "F1", "clave": "B", "puntos": 1},  // opcional
      "opciones": ["texto A", "texto B", "texto C", "texto D"]
      // las opciones reciben automáticamente el valor "A", "B", "C"...
      // o, si necesitas valores propios (p. ej. puntajes por opción):
      // "opciones": [{"texto": "...", "valor": "3"}, {"texto": "...", "valor": "0"}]
    }
  ],
  "algoritmo": {                     // opcional: solo si ya se tienen los datos oficiales
    "nombre": "...", "tipo_calculo": "por_clave",
    "factores": [{"codigo": "F1", "nombre": "...",
                  "escalas": [{"codigo": "...", "nombre": "...",
                               "valor_min": 0, "valor_max": 10,
                               "descripcion": "interpretación oficial"}]}]
  }
}
```

Tipos de pregunta: `OPCION_UNICA`, `OPCION_MULTIPLE`, `VERDADERO_FALSO`,
`ESCALA`, `ASOCIACION`, `ORDENAMIENTO`, `IMAGEN`, `TEXTO`, `ESTIMULO_VISUAL`.
Estrategias de `tipo_calculo`: `suma`, `puntuacion_directa`, `promedio`,
`ponderacion`, `por_clave`, `percentil`, `regla_condicional`.

## Regla de oro: el cargador no inventa nada

Carga únicamente lo que el archivo contiene. **No** completa ni infiere
claves, puntajes, pesos, baremos ni interpretaciones. Una evaluación
cargada sin `algoritmo` funciona (se asigna, se contesta, se finaliza)
pero queda en `COMPLETADA`: **no se califica** hasta que DPRH aporte los
datos de calificación, en lugar de "calificarse" con un 0 engañoso.

## Cómo agregar la calificación después

Los datos de calificación vienen de la documentación oficial de cada
prueba. Cuando se tengan:

1. Se agregan al mismo archivo JSON (`configuracion` por pregunta y/o el
   bloque `algoritmo`).
2. Se carga con `--version-nueva`. Las asignaciones ya hechas conservan
   la versión con la que se asignaron; las nuevas usan la vigente.
3. Si la evaluación ya tenía un algoritmo, **no se modifica** (el
   cargador avisa); se edita desde el panel, en *Evaluaciones*.

Qué necesita cada tipo de calificación:

| Si la prueba se califica por... | Hay que aportar |
|---|---|
| Una respuesta correcta por pregunta (`por_clave`) | La opción correcta de cada pregunta (`"clave": "B"`) y los puntos |
| Puntaje distinto por opción (`suma`) | El valor numérico de cada opción (`{"texto": ..., "valor": "3"}`) |
| Baremos / percentiles | La tabla de rangos (`tabla_percentiles` / `reglas`) |
| Interpretación por rangos | Las escalas con su `valor_min`, `valor_max` y descripción oficial |

## Qué conviene revisar de una evaluación transcrita

Una transcripción desde imágenes puede traer errores de lectura. Las
pruebas automáticas verifican la **estructura** (30 preguntas, 4 opciones
cada una, sin duplicados) y algunas frases puntuales, pero **no pueden
comparar cada palabra contra el original**: conviene una revisión
humana del texto contra la fuente.

## Estado actual

| Evaluación | Archivo | Contenido | Calificación |
|---|---|---|---|
| Moss | `moss.json` | 30 preguntas × 4 opciones (transcritas de capturas) | Pendiente: sin clave/baremos |
