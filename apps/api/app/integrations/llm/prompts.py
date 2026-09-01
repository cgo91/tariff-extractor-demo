"""Prompt templates for the Claude calls.

Kept as module constants so the wording can be reviewed and tuned without
reading through the client code. The prompts are written in Spanish because the
catalog, the descriptions and the justification shown to the user are all in
Spanish.
"""

from app.domain.models import ProductExtraction, TariffItem

EXTRACTION_SYSTEM_PROMPT = """\
Eres un perito clasificador aduanal mexicano. Observas la fotografía de una \
mercancía de electrónica de consumo o de periféricos de cómputo y describes \
únicamente lo que puedes ver o inferir con seguridad razonable.

Reglas:
- No inventes marca, modelo ni especificaciones. Si un dato no es legible, \
devuelve null en ese campo.
- `function` describe para qué sirve el producto, no cómo se ve.
- `search_keywords` son términos genéricos en español con los que buscarías la \
mercancía en la TIGIE (por ejemplo «audífonos», «auriculares», «inalámbricos»), \
nunca la marca ni el modelo.
- Escribe en español, sin abreviaturas."""

EXTRACTION_USER_PROMPT = """\
Describe la mercancía de esta fotografía para su clasificación arancelaria."""


CLASSIFICATION_SYSTEM_PROMPT = """\
Eres un perito clasificador aduanal mexicano. Asignas la fracción arancelaria \
y el NICO de la TIGIE a una mercancía ya descrita, eligiendo de una lista \
cerrada de candidatos.

Reglas:
- Elige obligatoriamente una fracción de la lista de candidatos. No propongas \
ninguna otra, ni siquiera si crees que existe una mejor.
- Justifica con la Regla General 1 (los títulos de secciones y capítulos son \
indicativos; la clasificación se determina por los textos de partida y las \
notas) y la Regla General 6 (la comparación se hace entre subpartidas del \
mismo nivel).
- `confidence` refleja tu certeza real. Usa un valor menor a 0.6 cuando la \
mercancía admita dos lecturas legítimas en partidas distintas, cuando la \
fotografía no muestre lo necesario para decidir, o cuando ningún candidato \
describa bien la mercancía.
- En `alternatives` incluye las fracciones que consideraste y descartaste, con \
el motivo del descarte. Si la confianza es baja, la alternativa en competencia \
es obligatoria.
- Escribe la justificación en español, en un párrafo."""


def build_classification_prompt(
    extraction: ProductExtraction, candidates: list[TariffItem]
) -> str:
    """Render the user turn of the classification call."""
    return (
        "MERCANCÍA\n"
        f"{_render_extraction(extraction)}\n\n"
        "CANDIDATOS DEL CATÁLOGO TIGIE\n"
        f"{_render_candidates(candidates)}\n\n"
        "Elige la fracción y el NICO que correspondan, entre los candidatos "
        "anteriores."
    )


def build_retry_prompt(candidates: list[TariffItem], rejected_code: str) -> str:
    """Render the corrective turn used when the model left the candidate list.

    Naming the rejected code explicitly is what makes the second attempt
    reliable: a generic "try again" tends to produce the same answer.
    """
    valid_codes = ", ".join(sorted({item.tariff_code for item in candidates}))
    return (
        f"La fracción {rejected_code} no está en la lista de candidatos y no "
        "puede usarse.\n\n"
        f"Las únicas fracciones válidas son: {valid_codes}.\n\n"
        "Elige una de ellas. Si ninguna describe bien la mercancía, elige la "
        "más cercana y refleja esa incertidumbre con una confianza menor a 0.6, "
        "explicándola en la justificación."
    )


def _render_extraction(extraction: ProductExtraction) -> str:
    """Format the extracted features as a readable block."""
    lines = [
        f"Nombre: {extraction.name}",
        f"Función: {extraction.function}",
    ]
    if extraction.brand:
        lines.append(f"Marca: {extraction.brand}")
    if extraction.model:
        lines.append(f"Modelo: {extraction.model}")
    if extraction.material:
        lines.append(f"Material: {extraction.material}")
    if extraction.technical_specs:
        lines.append("Características: " + "; ".join(extraction.technical_specs))
    if extraction.visible_text:
        lines.append(f"Texto visible: {extraction.visible_text}")
    return "\n".join(lines)


def _render_candidates(candidates: list[TariffItem]) -> str:
    """Format the candidate list as one numbered line per tariff item."""
    return "\n".join(
        f"{index}. {item.tariff_code} · NICO {item.nico} · IGI "
        f"{item.igi_rate * 100:.0f}% · UMT {item.unit_of_measure}\n"
        f"   Partida: {item.heading_description or 'sin texto de partida'}\n"
        f"   Fracción: {item.description}"
        for index, item in enumerate(candidates, start=1)
    )
