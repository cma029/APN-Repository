import click
import ast
import json
import concurrent.futures
import hashlib
from pathlib import Path
from storage.json_storage_utils import (
    load_input_apns_and_matches,
    save_input_apns_and_matches
)
from apn_object import APN
from representations.truth_table_representation import TruthTableRepresentation
from cli_commands.cli_utils import format_generic_apn
from apn_invariants import compute_is_apn


@click.command("add-input")
@click.option("--poly", "-p", multiple=True,
        help=("Univariate Polynomial in the form '[(0,3), (1,9), ...]'. Requires --field-n if used."))
@click.option("--field-n", default=None, type=int, required=False, help=("GF(2^n) dimension (n). "
        "Required if using --poly. Not required if only using file-based inputs."))
@click.option("--irr-poly", default="", type=str,
        help="Irreducible polynomial string (e.g. 'x^6 + x^4 + x^3 + x + 1'), optional.")
@click.option("--tt-file", type=click.Path(exists=True), multiple=True,
        help=("Path to file where the first line is a field n integer and each subsequent line "
        "is one truth-table of length 2^n. Each line can use space, comma or surrounding braces."))
@click.option("--poly-file", type=click.Path(exists=True), multiple=True,
        help=("Path to file where the first line is field n integer and each subsequent line "
        "is a univariate polynomial represented by 'g' and 'x', optionally with bracketed citation.\n"
        "Example: g^15*x^48 + g^16*x^33 + x^3 [Some Citation]\n"
        "If --citation-all is used, that overrides any bracket in the file."))
@click.option("--citation", multiple=True,
        help="Attach a citation string for each APN, in order. E.g. --citation '[BL22]' multiple times.")
@click.option("--citation-all", default=None, type=str,
        help="If provided, all APNs from a --poly-file get the same citation (overrides bracketed ones).")
@click.option("--max-threads", default=None, type=int,
        help="Limit the number of parallel processes used. Default uses all available cores.")
def add_input_cli(poly, field_n, irr_poly, tt_file, poly_file, citation, citation_all, max_threads):
    """
    Adds user-specified APNs to storage/input_apns_and_matches.json.
      - Inline polynomials via --poly
      - Truth table files via --tt-file
      - Polynomial-based files via --poly-file
    """
    apn_list = load_input_apns_and_matches()
    existing_keys = set()

    # Check if we already have APNs stored in file for field n dimension consistency.
    existing_n = None
    if apn_list:
        # We check the dimension of the first APN. This becomes the "existing dimension".
        existing_n = apn_list[0].get("field_n", None)
        # Check that all APNs in the file have the same field_n dimension.
        for idx, apn_dict in enumerate(apn_list):
            fieldn = apn_dict.get("field_n", None)
            if fieldn != existing_n:
                raise click.ClickException(
                    f"APN index {idx} in storage has field_n={fieldn} != {existing_n} (mismatch in file).")

    # Rebuild existing APN(s) from dictionary and generate their final key.
    for existing_apn_dictionary in apn_list:
        key_value = _build_existing_key(existing_apn_dictionary)
        existing_keys.add(key_value)

    # Enforces that any new APN dimension matches existing_n, or set existing_n from that APN.
    def _ensure_dimension_consistency(new_field_n):
        nonlocal existing_n
        if existing_n is None:
            existing_n = new_field_n
        else:
            if new_field_n != existing_n:
                raise click.ClickException(
                    f"New APN dimension {new_field_n} does not match existing dimension {existing_n} in storage.")
            
    # New APNs from all sources.
    new_apns = []

    # Univariate polynomials as lists of tuples: --poly as input. Require a single dimension from --field-n.
    if poly:
        if field_n is None:
            raise click.ClickException("Error: --field-n is required when using the --poly option.")
        _ensure_dimension_consistency(field_n)

        for poly_str in poly:
            try:
                poly_tuples = ast.literal_eval(poly_str)
            except Exception as parse_exc:
                click.echo(f"Error parsing user polynomial '{poly_str}': {parse_exc}", err=True)
                continue

            apn_object = APN(poly_tuples, field_n, irr_poly)
            candidate_key = _build_key_from_apn(apn_object)
            if candidate_key in existing_keys:
                click.echo(f"Skipped duplicate polynomial {poly_str} (already in file).")
                continue

            new_apns.append(apn_object)
            existing_keys.add(candidate_key)

    # Truth table files: --tt-file as input.
    for tt_filepath_str in tt_file:
        file_path_object = Path(tt_filepath_str)
        if not file_path_object.is_file():
            click.echo(f"Error: File '{tt_filepath_str}' not found.", err=True)
            continue

        lines = [ln.strip() for ln in file_path_object.read_text().splitlines() if ln.strip()]
        if len(lines) < 2:
            click.echo(
                f"File '{tt_filepath_str}' does not have enough lines (field n + at least one truth table).", err=True)
            continue

        # The first line (field n).
        try:
            field_n_line = int(lines[0])
        except ValueError:
            click.echo(f"File '{tt_filepath_str}': first line must be integer field n.", err=True)
            continue
        _ensure_dimension_consistency(field_n_line)

        # The subsequent lines where each line is a Truth Table row.
        # Using concurrency for the Lagrange interpolation part.
        tasks_for_tt = []
        for idx, tt_line in enumerate(lines[1:]):
            tasks_for_tt.append((idx, tt_line, field_n_line, irr_poly))

        tt_apn_results = [None] * len(tasks_for_tt)
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_threads) as executor:
            future_map = {}
            for tdata in tasks_for_tt:
                fut = executor.submit(_build_apn_from_tt_worker, tdata)
                future_map[fut] = tdata[0]

            for done_fut in concurrent.futures.as_completed(future_map):
                local_idx = future_map[done_fut]
                try:
                    local_idx, built_apn = done_fut.result()
                    tt_apn_results[local_idx] = built_apn
                except Exception as e:
                    click.echo(f"Error building APN for TT index={local_idx} in '{tt_filepath_str}': {e}", err=True)
                    tt_apn_results[local_idx] = None

        # Filter out the None results.
        for idx, apn_object in enumerate(tt_apn_results):
            if apn_object is None:
                continue
            candidate_key = _build_key_from_apn(apn_object)
            if candidate_key in existing_keys:
                file_line_number = idx + 2
                click.echo(f"Skipped duplicate truth table line {file_line_number} "
                           f"in '{tt_filepath_str}' (already in file).")
                continue

            new_apns.append(apn_object)
            existing_keys.add(candidate_key)

    # Univariate polynomial-based files: --poly-file as input.
    for poly_path_str in poly_file:
        file_path_object = Path(poly_path_str)
        if not file_path_object.is_file():
            click.echo(f"Error: File '{poly_path_str}' not found.", err=True)
            continue

        lines = [ln.strip() for ln in file_path_object.read_text().splitlines() if ln.strip()]
        if len(lines) < 2:
            click.echo(
                f"File '{poly_path_str}' does not have enough lines (field n + at least one polynomial).", err=True)
            continue

        # The first line (field n).
        try:
            field_n_line = int(lines[0])
        except ValueError:
            click.echo(f"File '{poly_path_str}': first line must be integer field n.", err=True)
            continue
        _ensure_dimension_consistency(field_n_line)

        # The subsequent lines where each line is a univariate polynomial plus optional [citation].
        for line_no, line_text in enumerate(lines[1:], start=2):
            if not line_text:
                continue

            # Trim trailing comma.
            line_text = line_text.rstrip(',')

            if citation_all:
                poly_part = line_text.split('[', 1)[0].strip()
                bracketed_citation = citation_all.strip()
            else:
                poly_part, bracketed_citation = _extract_citation(line_text)

            try:
                poly_list_literal = _parse_line_to_univ_list_literal(poly_part)
            except ValueError as error:
                click.echo(f"Error in '{poly_path_str}' line {line_no}: {error}", err=True)
                continue

            # Evaluate the literal as a list of (coefficient_exp, monomial_exp).
            try:
                poly_list_data = ast.literal_eval(poly_list_literal)
            except Exception as parse_exc:
                click.echo(f"Error building polynomial on line {line_no} in '{poly_path_str}': {parse_exc}", err=True)
                continue

            apn_object = APN(poly_list_data, field_n_line, irr_poly)
            if bracketed_citation:
                apn_object.invariants["citation"] = bracketed_citation

            candidate_key = _build_key_from_apn(apn_object)
            if candidate_key in existing_keys:
                click.echo(f"Skipped duplicate polynomial on line {line_no} in '{poly_path_str}' (already in file).")
                continue

            new_apns.append(apn_object)
            existing_keys.add(candidate_key)

    # Exit if no new APNs were found.
    if not new_apns:
        click.echo("No new APNs were added.")
        return

    # Check if each new APN is_apn (differential uniformity == 2).
    tasks = [(idx_val, apn_obj) for idx_val, apn_obj in enumerate(new_apns)]
    max_workers = max_threads or None
    results_map = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_list = [executor.submit(_compute_is_apn_task, single_task) for single_task in tasks]
        for done_future in concurrent.futures.as_completed(future_list):
            idx_val, updated_apn_obj = done_future.result()
            results_map[idx_val] = updated_apn_obj

    final_added_apns = []
    for idx_val in range(len(new_apns)):
        updated_apn_obj = results_map.get(idx_val)
        if updated_apn_obj and updated_apn_obj.invariants.get("is_apn", False):
            final_added_apns.append(updated_apn_obj)

    if not final_added_apns:
        click.echo("The new APNs are actually not APNs (differential uniformity != 2).")
        return

    # If the user supplied a --citation, attach the citation (in order) to the final APN(s).
    final_entries = []
    citation_idx = 0
    for citation_idx, final_apn_object in enumerate(final_added_apns):
        if citation_idx < len(citation):
            final_apn_object.invariants["citation"] = citation[citation_idx]
            citation_idx += 1

        if hasattr(final_apn_object.representation, "univariate_polynomial"):
            stored_poly = final_apn_object.representation.univariate_polynomial
        else:
            stored_poly = []

        cached_tt = final_apn_object._get_truth_table_list()

        entry_dictionary = {
            "poly": stored_poly,
            "field_n": final_apn_object.field_n,
            "irr_poly": final_apn_object.irr_poly,
            "invariants": final_apn_object.invariants,
            "matches": [],
            "cached_tt": cached_tt
        }
        final_entries.append(entry_dictionary)

    apn_list.extend(final_entries)
    save_input_apns_and_matches(apn_list)

    if final_entries:
        click.echo("\nNewly Added APNs:")
        click.echo("-" * 100)
        for index_added, entry_dictionary in enumerate(final_entries, start=1):
            if entry_dictionary["poly"]:
                show_apn = APN(entry_dictionary["poly"], entry_dictionary["field_n"], entry_dictionary["irr_poly"])
            else:
                show_apn = APN.from_representation(TruthTableRepresentation(entry_dictionary["cached_tt"]),
                    entry_dictionary["field_n"], entry_dictionary["irr_poly"])
            show_apn.invariants = entry_dictionary["invariants"]
            click.echo(format_generic_apn(show_apn, f"APN {index_added}"))
            click.echo("-" * 100)


def _compute_is_apn_task(task):
    idx_value, apn_object = task
    compute_is_apn(apn_object)
    return (idx_value, apn_object)


def _build_existing_key(apn_dictionary):
    # Recreate APN from dictionary, then produce the final key.
    poly_list = apn_dictionary.get("poly", [])
    field_n = apn_dictionary.get("field_n", 0)
    irr_poly = apn_dictionary.get("irr_poly", "")
    cached_tt = apn_dictionary.get("cached_tt", [])

    if poly_list:
        apn_object = APN(poly_list, field_n, irr_poly)
        if cached_tt:
            apn_object._cached_tt_list = cached_tt
    else:
        apn_object = APN.from_cached_tt(cached_tt, field_n, irr_poly)

    return _build_key_from_apn(apn_object)


def _build_key_from_apn(apn_object):
    # To detect duplicates. Produces a JSON-based hash key.
    if hasattr(apn_object.representation, "univariate_polynomial"):
        sorted_poly = sorted(
            apn_object.representation.univariate_polynomial, key=lambda x: (x[0], x[1]))
        return json.dumps(["POLY", apn_object.field_n, apn_object.irr_poly, sorted_poly], sort_keys=True)
    else:
        # Truth Table-based.
        hasher = hashlib.sha256()
        tt_values = apn_object._get_truth_table_list()
        for value in tt_values:
            hasher.update(value.to_bytes(4, 'little'))
        tt_hash = hasher.hexdigest()

        return json.dumps(["TT", apn_object.field_n, apn_object.irr_poly, tt_hash], sort_keys=True)


def _parse_tt_values(line_str):
    # Returns a list of integers or None if parsing fails.
    line_str = line_str.strip()

    # If a line ends with }, then remove the trailing comma.
    if line_str.endswith("},"):
        line_str = line_str[:-1].rstrip()

    # Check for curly braces.
    if line_str.startswith("{") and line_str.endswith("}"):
        inside = line_str[1:-1].strip()
        if not inside:
            return []
        candidates = [x.strip() for x in inside.split(",")]
        try:
            return list(map(int, candidates))
        except:
            return None

    # Check for comma-separators.
    if "," in line_str:
        parts = [x.strip() for x in line_str.split(",")]
        try:
            return list(map(int, parts))
        except:
            return None

    # Last option, assume space-separated.
    parts = line_str.split()
    try:
        return list(map(int, parts))
    except:
        return None


def _extract_citation(line: str):
    # Attempts to extract bracketed [Citation] from a line.
    start_idx = line.rfind('[')
    end_idx = line.rfind(']')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        citation_str = line[start_idx+1:end_idx].strip()
        poly_part = line[:start_idx].strip()
        return (poly_part, citation_str)
    else:
        return (line, "")


def _parse_line_to_univ_list_literal(line: str) -> str:
    # Convert a string polynomial like 'g^15*x^48 + x^3' into a Python list literal: "[(15,48),(0,3)]".
    terms = [ter.strip() for ter in line.split('+')]
    tuple_list = []
    for term in terms:
        coeff_exp, mon_exp = _parse_single_term(term)
        tuple_list.append((coeff_exp, mon_exp))

    return "[" + ",".join(f"({coeff},{mon})" for (coeff, mon) in tuple_list) + "]"


def _parse_single_term(term: str):
    term = term.strip().lower()
    if term == '1':
        return (0, 0)

    if '*' in term:
        parts = [part.strip() for part in term.split('*')]
        if len(parts) != 2:
            raise ValueError(f"Unrecognized polynomial term '{term}'. Expected 2 parts separated by '*'.")
        left_segment, right_segment = parts
        coeff_exp = _parse_coefficient(left_segment)
        mon_exp = _parse_monomial(right_segment)
        return (coeff_exp, mon_exp)
    else:
        # Just a single coefficient, or just a single monomial.
        if term.startswith('g'):
            coeff_exp = _parse_coefficient(term)
            return (coeff_exp, 0)
        else:
            mon_exp = _parse_monomial(term)
            return (0, mon_exp)


def _parse_coefficient(segment: str) -> int:
    # Coefficient format: 'g' = 1, 'g^77' = 77.
    segment = segment.strip()
    if segment == 'g':
        return 1
    if segment.startswith('g^'):
        exponent_str = segment[2:].strip()
        if not exponent_str.isdigit():
            raise ValueError(f"Unrecognized coefficient '{segment}'. Expected 'g^<int>'.")
        return int(exponent_str)
    raise ValueError(f"Unrecognized coefficient '{segment}'. Expected 'g' or 'g^<int>'.")


def _parse_monomial(segment: str) -> int:
    # Monomial format: 'x' = 1, 'x^77' = 77.
    segment = segment.strip()
    if segment == 'x':
        return 1
    if segment.startswith('x^'):
        exponent_str = segment[2:].strip()
        if not exponent_str.isdigit():
            raise ValueError(f"Unrecognized monomial '{segment}'. Expected 'x^<int>'.")
        return int(exponent_str)
    raise ValueError(f"Unrecognized monomial '{segment}'. Expected 'x' or 'x^<int>'.")


def _build_apn_from_tt_worker(task):
    # Worker function for concurrency: Truth table -> Lagrange interpolation -> APN object.
    idx, tt_line, field_n_line, irr_poly = task
    tt_values = _parse_tt_values(tt_line)
    if tt_values is None:
        raise ValueError(f"Could not parse truth table line: {tt_line}")
    if len(tt_values) != (1 << field_n_line):
        raise ValueError(f"Truth table length mismatch for line: {tt_line}")
    tt_rep = TruthTableRepresentation(tt_values)
    apn_object = APN.from_representation(tt_rep, field_n_line, irr_poly)
    return (idx, apn_object)