#!/usr/bin/env python3
"""Convert RDF/Turtle files to JSON-LD and RDF/XML.

Usage examples:
    python convert_rdf.py RDF_Turtle_finale.ttl
    python convert_rdf.py ./cartella_con_ttl
    python convert_rdf.py input.ttl -o ./output

Requires:
    pip install rdflib
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

from rdflib import Graph
from rdflib.compare import isomorphic


def output_paths(input_path: Path, output_dir: Path) -> tuple[Path, Path]:
    stem = input_path.stem

    # Normalize only a final occurrence of "finale" to "Finale"
    # in generated filenames. The RDF content is not modified.
    stem = re.sub(r"finale$", "Finale", stem, flags=re.IGNORECASE)

    return (
        output_dir / f"{stem}.jsonld",
        output_dir / f"{stem}.rdf",
    )


def convert_file(ttl_path: Path, output_dir: Path, verify: bool = True) -> tuple[Path, Path, int]:
    """Convert one Turtle file and optionally verify graph equivalence."""
    output_dir.mkdir(parents=True, exist_ok=True)

    graph = Graph()
    graph.parse(ttl_path, format="turtle")

    jsonld_path, rdfxml_path = output_paths(ttl_path, output_dir)

    # Expanded JSON-LD intentionally keeps full IRIs and explicit datatypes.
    # This avoids losing details such as an explicit xsd:string during round-trip.
    jsonld_text = graph.serialize(
        format="json-ld",
        indent=2,
        ensure_ascii=False,
    )
    jsonld_path.write_text(jsonld_text, encoding="utf-8")

    # RDF/XML. RDFLib's "pretty-xml" serializer creates a more readable file.
    rdfxml_text = graph.serialize(format="pretty-xml", encoding=None)
    rdfxml_path.write_text(rdfxml_text, encoding="utf-8")

    if verify:
        graph_jsonld = Graph().parse(jsonld_path, format="json-ld")
        graph_rdfxml = Graph().parse(rdfxml_path, format="xml")

        if not isomorphic(graph, graph_jsonld):
            raise RuntimeError(f"JSON-LD verification failed for {ttl_path.name}")
        if not isomorphic(graph, graph_rdfxml):
            raise RuntimeError(f"RDF/XML verification failed for {ttl_path.name}")

    return jsonld_path, rdfxml_path, len(graph)


def find_turtle_files(path: Path) -> Iterable[Path]:
    """Accept either one .ttl file or a directory containing .ttl files."""
    if path.is_file():
        if path.suffix.lower() != ".ttl":
            raise ValueError("The input file must have the .ttl extension.")
        yield path
        return

    if path.is_dir():
        files = sorted(p for p in path.glob("*.ttl") if p.is_file())
        if not files:
            raise ValueError(f"No .ttl files found in: {path}")
        yield from files
        return

    raise FileNotFoundError(f"Input path not found: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert RDF/Turtle (.ttl) to JSON-LD (.jsonld) and RDF/XML (.rdf)."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="A .ttl file or a directory containing .ttl files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output directory. Default: same directory as each input file.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip semantic equivalence verification of generated files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        ttl_files = list(find_turtle_files(args.input))

        for ttl_path in ttl_files:
            out_dir = args.output if args.output is not None else ttl_path.parent
            jsonld_path, rdfxml_path, triples = convert_file(
                ttl_path,
                out_dir,
                verify=not args.no_verify,
            )

            print(f"OK: {ttl_path.name} ({triples} triples)")
            print(f"  JSON-LD : {jsonld_path}")
            print(f"  RDF/XML : {rdfxml_path}")

        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
