from pathlib import Path
import re
import sys


# ============================================================
# REGEX PER IL CONTENUTO DI time_reference
# ============================================================

# Data completa: 1986-12-31
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Intervallo di anni: 1756-1762
YEAR_RANGE_RE = re.compile(r"^(\d{4})-(\d{4})$")

# Riferimento espresso come secolo o porzione di secolo:
# XVII secolo
# Metà XVII secolo
# Fine XIX secolo
# Seconda metà XIX secolo
CENTURY_RE = re.compile(r"\bsecolo\b", re.IGNORECASE)


# ============================================================
# BLOCCO TURTLE GENERATO DA MATEY
#
# Esempio:
#
# <.../TimeReference/0800686820> rdf:type cult:TimeReference ;
#     l0:name "1986-12-31" .
#
# Lo script modifica SOLO blocchi con questa struttura.
# ============================================================

TIME_REFERENCE_BLOCK_RE = re.compile(
    r'(?m)'
    r'^(?P<subject><https://example\.lod\.it/data/TimeReference/[^>\r\n]+>)'
    r'[ \t]+rdf:type[ \t]+cult:TimeReference[ \t]*;'
    r'(?P<newline>\r?\n)'
    r'(?P<indent>[ \t]+)'
    r'l0:name[ \t]+'
    r'(?P<literal>"(?:\\.|[^"\\])*")'
    r'[ \t]*\.$'
)


def turtle_string_value(literal: str) -> str:
    """
    Restituisce il contenuto lessicale di una semplice stringa Turtle
    racchiusa tra doppi apici.

    Per la classificazione temporale ci interessano soprattutto cifre,
    trattini e la parola 'secolo'. Gestiamo comunque le sequenze di escape
    più comuni senza riserializzare il Turtle.
    """
    value = literal[1:-1]

    replacements = {
        r"\\": "\\",
        r"\"": '"',
        r"\n": "\n",
        r"\r": "\r",
        r"\t": "\t",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value


def enrich_block(match: re.Match) -> str:
    subject = match.group("subject")
    newline = match.group("newline")
    indent = match.group("indent")
    literal = match.group("literal")

    value = turtle_string_value(literal).strip()

    # --------------------------------------------------------
    # DATE REFERENCE
    # --------------------------------------------------------
    if DATE_RE.fullmatch(value):
        return (
            f"{subject} rdf:type cult:TimeReference, cult:DateReference ;"
            f"{newline}"
            f"{indent}l0:name {literal} ;"
            f"{newline}"
            f'{indent}tiapit:date {literal}^^xsd:date .'
        )

    # --------------------------------------------------------
    # YEAR RANGE
    # --------------------------------------------------------
    year_match = YEAR_RANGE_RE.fullmatch(value)

    if year_match:
        start_year = year_match.group(1)
        end_year = year_match.group(2)

        return (
            f"{subject} rdf:type cult:TimeReference, cult:YearRange ;"
            f"{newline}"
            f"{indent}l0:name {literal} ;"
            f"{newline}"
            f'{indent}cult:startYear "{start_year}"^^xsd:gYear ;'
            f"{newline}"
            f'{indent}cult:endYear "{end_year}"^^xsd:gYear .'
        )

    # --------------------------------------------------------
    # CENTURY REFERENCE
    # --------------------------------------------------------
    if CENTURY_RE.search(value):
        return (
            f"{subject} rdf:type cult:TimeReference, cult:CenturyReference ;"
            f"{newline}"
            f"{indent}l0:name {literal} ;"
            f"{newline}"
            f"{indent}cult:centuryLabel {literal}^^xsd:string ."
        )

    # Valore non riconosciuto:
    # restituiamo il blocco IDENTICO, senza modificarlo.
    return match.group(0)


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print(
            "Uso:\n"
            "  python arricchisci_time_reference_preserva_turtle.py input.ttl\n"
            "oppure:\n"
            "  python arricchisci_time_reference_preserva_turtle.py input.ttl output.ttl"
        )
        raise SystemExit(1)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"Errore: file non trovato: {input_path}")
        raise SystemExit(1)

    if len(sys.argv) == 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = input_path.with_name(
            input_path.stem + "_arricchito.ttl"
        )

    # newline="" evita conversioni automatiche CRLF/LF.
    with input_path.open("r", encoding="utf-8", newline="") as f:
        original = f.read()

    # Contatori prima della sostituzione
    recognized_dates = 0
    recognized_ranges = 0
    recognized_centuries = 0
    unknown = []

    for m in TIME_REFERENCE_BLOCK_RE.finditer(original):
        value = turtle_string_value(m.group("literal")).strip()

        if DATE_RE.fullmatch(value):
            recognized_dates += 1
        elif YEAR_RANGE_RE.fullmatch(value):
            recognized_ranges += 1
        elif CENTURY_RE.search(value):
            recognized_centuries += 1
        else:
            unknown.append(value)

    # Sostituisce SOLO i blocchi TimeReference riconosciuti.
    enriched = TIME_REFERENCE_BLOCK_RE.sub(enrich_block, original)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        f.write(enriched)

    print("Arricchimento completato.")
    print(f"DateReference: {recognized_dates}")
    print(f"YearRange: {recognized_ranges}")
    print(f"CenturyReference: {recognized_centuries}")
    print(f"Non riconosciuti: {len(unknown)}")

    for value in unknown:
        print(f"  - {value}")

    print(f"File creato: {output_path}")
    print()
    print("Il resto del Turtle non viene riserializzato:")
    print("- prefissi mantenuti")
    print("- ordine dei blocchi mantenuto")
    print("- ordine delle triple non temporali mantenuto")
    print("- formattazione non temporale mantenuta")


if __name__ == "__main__":
    main()
