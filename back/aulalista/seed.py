"""Datos simulados. Todo lo definido aquí es de ejemplo y se rotula como tal."""
from __future__ import annotations

SIMULATED_SOURCE_LABEL = (
    "Módulo simulado de ejemplo. No es currículo oficial ni un curso identificado de APRENDE PERÚ."
)

MODULES = {
    "mod-escucha-activa": {
        "id": "mod-escucha-activa",
        "version": "1.0",
        "title": "Escucha activa y diálogo respetuoso",
        "sourceLabel": SIMULATED_SOURCE_LABEL,
        "isSimulated": True,
        "fragments": [
            {
                "id": "M1",
                "text": (
                    "Escuchar a otra persona requiere darle tiempo para terminar y atender a lo que "
                    "expresa. En una actividad por parejas se pueden alternar los papeles de quien "
                    "habla y quien escucha."
                ),
            },
            {
                "id": "M2",
                "text": (
                    "Parafrasear consiste en expresar con palabras propias lo que se entendió y "
                    "preguntar a la otra persona si esa interpretación es correcta. La persona que "
                    "habló puede aclarar o corregir."
                ),
            },
            {
                "id": "M3",
                "text": (
                    "Las preguntas de aclaración buscan comprender mejor el mensaje. Se puede cerrar "
                    "una actividad pidiendo explicar una idea escuchada y describir cómo se comprobó "
                    "su comprensión."
                ),
            },
        ],
    }
}

DEFAULT_CASE = {
    "moduleId": "mod-escucha-activa",
    "grade": "Cuarto de primaria",
    "durationMinutes": 45,
    "materials": ["pizarra", "papel", "lápiz"],
    "notes": "",
}

USERS = {
    "u-demo": "Profe Demo",
    "u-sim-autor": "Docente simulado (autor)",
    "u-sim-1": "Docente simulado 1",
    "u-sim-2": "Docente simulado 2",
    "u-sim-3": "Docente simulado 3",
}
DEMO_USER_ID = "u-demo"

# Experiencia compartida simulada. Sirve para mostrar la valoración y la adaptación.
SEED_EXPERIENCE_ID = "exp-sim-escucha-v1"
SEED_EXPERIENCE = {
    "id": SEED_EXPERIENCE_ID,
    "authorId": "u-sim-autor",
    "title": "Escucha activa por parejas (versión 1)",
    "purpose": "Practicar la escucha activa alternando los papeles de quien habla y quien escucha.",
    "grade": "Cuarto de primaria",
    "materials": ["pizarra", "papel", "lápiz"],
    "description": (
        "Trabajo por parejas. Una persona cuenta una experiencia breve y la otra la parafrasea y "
        "pregunta si entendió bien. Luego se intercambian los papeles."
    ),
    "observation": (
        "Las instrucciones iniciales fueron largas y tuve que repetirlas. Algunas parejas "
        "empezaron antes de entender la dinámica."
    ),
    "improvement": "Dividir las instrucciones en tres pasos y mostrar un ejemplo antes de empezar.",
    "context": {
        "moduleId": "mod-escucha-activa",
        "moduleVersion": "1.0",
        "grade": "Cuarto de primaria",
        "durationMinutes": 45,
        "materials": ["pizarra", "papel", "lápiz"],
        "notes": "",
    },
    "content": {
        "title": "Escucha activa por parejas (versión 1)",
        "purpose": "Practicar la escucha activa alternando los papeles de quien habla y quien escucha.",
        "grade": "Cuarto de primaria",
        "durationMinutes": 45,
        "materials": ["pizarra", "papel", "lápiz"],
        "activities": [
            {
                "id": "a1",
                "title": "Explicación de la dinámica",
                "minutes": 15,
                "description": (
                    "Explicar oralmente todas las reglas de la actividad antes de formar las parejas."
                ),
                "references": ["M1"],
            },
            {
                "id": "a2",
                "title": "Hablar y escuchar por parejas",
                "minutes": 15,
                "description": "Cada pareja alterna los papeles de quien habla y quien escucha.",
                "references": ["M1", "M2"],
            },
            {
                "id": "a3",
                "title": "Parafrasear y aclarar",
                "minutes": 10,
                "description": (
                    "Quien escucha dice con sus palabras lo entendido y pregunta si es correcto."
                ),
                "references": ["M2"],
            },
            {
                "id": "a4",
                "title": "Cierre",
                "minutes": 5,
                "description": "Cada estudiante explica una idea escuchada.",
                "references": ["M3"],
            },
        ],
        "expectedEvidence": "Cada estudiante explica con sus palabras una idea que escuchó.",
    },
    # Cada valoración: (revisor, criterios, contexto). Promedios 4,5 · 4,25 · 4,5 -> 4,4.
    "ratings": [
        ("u-sim-1", [5, 4, 4, 5], "Cuarto de primaria · pizarra y papel"),
        ("u-sim-2", [4, 4, 5, 4], "Cuarto de primaria · pizarra y papel"),
        ("u-sim-3", [5, 5, 4, 4], "Quinto de primaria · pizarra y papel"),
    ],
}
