import click
from pathlib import Path
from click.testing import CliRunner
from cli_commands.add_input_cmd import add_input_cli

@click.command("bulk-import")
@click.option("--file", "file_path", required=True,
              type=click.Path(exists=True, dir_okay=False),
              help="Path to the bulk import file. First line is dimension, then one polynomial per line.")
@click.option("--irr-poly", default=None, type=str,
              help="If provided, sets the irreducible polynomial for all APNs in the file.")
@click.option("--citation-all", default=None, type=str,
              help="If provided, all APNs get the same citation string, ignoring bracketed citations.")
def bulk_import_cli(file_path, irr_poly, citation_all):
    """
    Reads dimension from the first line of the file, then each subsequent line is a univariate polynomial
    that can include alpha powers 'g^k' and monomial powers 'x^m' plus an optional [citation] string.
    Example line: g^15*x^48 + g^16*x^33 + g^16*x^18 + x^17 + x^3 [L. Budaghyan, C. Carlet & G. Leander (2009)]
    """
    file_path_object = Path(file_path)
    all_lines = file_path_object.read_text().splitlines()
    if not all_lines:
        click.echo("The file is empty.")
        return

    # First line is the field n dimension.
    try:
        dimension = int(all_lines[0].strip())
    except ValueError:
        click.echo("First line of file must be an integer dimension (e.g. '8').")
        return

    # Collect polynomials and citations from subsequent lines.
    polynomials_str_list = []
    citations_str_list   = []

    for line_no, line in enumerate(all_lines[1:], start=2):
        line = line.strip().rstrip(',')
        if not line:
            continue

        if citation_all:
            poly_part = line.split('[', 1)[0].strip()
            citation_part = citation_all.strip()
        else:
            poly_part, citation_part = _extract_citation(line)

        try:
            poly_list_literal = _parse_line_to_univ_list_literal(poly_part)
        except ValueError as err:
            click.echo(f"Error on line {line_no}: {err}")
            return

        polynomials_str_list.append(poly_list_literal)
        citations_str_list.append(citation_part)

    if not polynomials_str_list:
        click.echo("No polynomial lines found after the first line (dimension).")
        return

    runner = CliRunner()
    # Always provide the field n dimension.
    invoke_args = ["--field-n", str(dimension)]
    # Only pass --irr-poly if provided.
    if irr_poly and irr_poly.strip():
        invoke_args.extend(["--irr-poly", irr_poly.strip()])

    # Add each polynomial plus its citation.
    for poly_literal, cit_string in zip(polynomials_str_list, citations_str_list):
        invoke_args.extend(["--poly", poly_literal])
        if cit_string:
            invoke_args.extend(["--citation", cit_string])

    # Call add_input_cmd in-process.
    result = runner.invoke(add_input_cli, invoke_args)
    click.echo(result.output)


def _extract_citation(line: str):
    citation_part = ""
    # Find the last '[' and closing ']' if present.
    start_idx = line.rfind('[')
    end_idx   = line.rfind(']')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        citation_str = line[start_idx+1:end_idx].strip()
        poly_part    = line[:start_idx].strip()
        return (poly_part, citation_str)
    else:
        # No bracket means no citation.
        return (line, "")


def _parse_line_to_univ_list_literal(line: str) -> str:
    """    
    The polynomials are parsed into a string that is a Python literal for a list-of-tuples
    like "[(32,96),(7,80),...]", and each list is fed to 'add-input' as a --poly argument.
    """
    terms = [t.strip() for t in line.split('+')]
    tuple_list = []

    for term in terms:
        coeff_exp, mon_exp = _parse_single_term(term)
        tuple_list.append((coeff_exp, mon_exp))

    literal_str = "[" + ",".join(f"({c},{m})" for (c, m) in tuple_list) + "]"
    return literal_str


def _parse_single_term(term: str):
    # Parse a single term like 'g^32*x^96'. Return (coefficient_exp, monomial_exp) as integers.
    term = term.strip().lower()
    if term == '1':
        return (0, 0)

    # If there's a '*', handle split into left=coefficient, right=monomial.
    if '*' in term:
        parts = [p.strip() for p in term.split('*')]
        if len(parts) != 2:
            raise ValueError(f"Unrecognized polynomial term '{term}'. Expected 2 parts separated by '*'.")
        left_segment, right_segment = parts
        coeff_exp = _parse_coefficient(left_segment)
        mon_exp   = _parse_monomial(right_segment)
        return (coeff_exp, mon_exp)
    else:
        # No '*'. So either purely coefficient or purely monomial.
        # e.g. 'g^32' => (32, 0), or 'x^66' => (0,66).
        if term.startswith('g'):
            # Parse coefficient, mon_exp=0.
            coeff_exp = _parse_coefficient(term)
            return (coeff_exp, 0)
        else:
            # Parse monomial, coeff_exp=0.
            mon_exp = _parse_monomial(term)
            return (0, mon_exp)


def _parse_coefficient(segment: str) -> int:
    segment = segment.strip()
    if segment == 'g':
        return 1
    if segment.startswith('g^'):
        exponent_str = segment[2:].strip()
        if not exponent_str.isdigit():
            raise ValueError(f"Unrecognized alpha coefficient '{segment}'. Expected 'g^<int>'.")
        return int(exponent_str)
    raise ValueError(f"Unrecognized alpha coefficient '{segment}'. Expected 'g' or 'g^<int>'.")


def _parse_monomial(segment: str) -> int:
    segment = segment.strip()
    if segment == 'x':
        return 1
    if segment.startswith('x^'):
        exponent_str = segment[2:].strip()
        if not exponent_str.isdigit():
            raise ValueError(f"Unrecognized monomial '{segment}'. Expected 'x^<int>'.")
        return int(exponent_str)
    raise ValueError(f"Unrecognized monomial '{segment}'. Expected 'x' or 'x^<int>'.")