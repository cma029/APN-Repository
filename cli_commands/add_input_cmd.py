import click
import ast
import json
import re
import concurrent.futures
import hashlib
from pathlib import Path
from storage.json_storage_utils import (
    load_input_vbfs_and_matches,
    save_input_vbfs_and_matches
)
from vbf_object import VBF
from representations.truth_table_representation import TruthTableRepresentation
from cli_commands.cli_utils import format_generic_vbf, build_vbf_from_dict
from registry import REG


@click.command("add-input")
@click.option("--poly", "-p", multiple=True,
        help=("Univariate Polynomial in the form '[(0,3), (1,9), ...]'. Requires --dim if used."))
@click.option("--dim", "dim_n", default=None, type=int, required=False, help=("GF(2^n) dimension (n). "
        "Required if using --poly. Not required if only using file-based inputs."))
@click.option("--irr-poly", default="", type=str,
        help="Irreducible polynomial string (e.g. 'x^6 + x^4 + x^3 + x + 1'), optional.")
@click.option("--tt-file", type=click.Path(exists=True), multiple=True,
        help=("Path to file where the first line is a dimension n integer and each subsequent line "
        "is one truth-table of length 2^n. Each line can use space, comma or surrounding braces."))
@click.option("--poly-file", type=click.Path(exists=True), multiple=True,
        help=("Path to file where the first line is dimension n integer and each subsequent line "
        "is a univariate polynomial represented by 'g' and 'x', optionally with bracketed citation.\n"
        "Example: g^15*x^48 + g^16*x^33 + x^3 [Some Citation]\n"
        "If --citation-all is used, that overrides any bracket in the file."))
@click.option("--citation", multiple=True,
        help="Attach a citation string for each APN, in order. E.g. --citation '[BL22]' multiple times.")
@click.option("--citation-all", default=None, type=str,
        help="If provided, all APNs from a --poly-file get the same citation (overrides bracketed ones).")
@click.option("--max-threads", default=None, type=int,
        help="Limit the number of parallel processes used. Default uses all available cores.")
def add_input_cli(poly, dim_n, irr_poly, tt_file, poly_file, citation, citation_all, max_threads):
    """
        Adds user-specified Vectorial Boolean Functions (VBFs) to storage/input_vbfs_and_matches.json.
      - Inline polynomials via --poly
      - Truth table files via --tt-file
      - Polynomial-based files via --poly-file
    """
    vbf_list = load_input_vbfs_and_matches()
    existing_keys = set()

    # Check dimension consistency with existing VBFs.
    existing_dimension = None
    if vbf_list:
        # We check the dimension of the first VBF. This becomes the "existing dimension".
        existing_dimension = vbf_list[0].get("field_n", None)
        for idx, existing_dictionary in enumerate(vbf_list):
            dimension_check = existing_dictionary.get("field_n", None)
            if dimension_check != existing_dimension:
                raise click.ClickException(
                    f"VBF index {idx} in storage has field_n={dimension_check} != {existing_dimension}."
                )

    # Rebuild existing VBF(s) from dictionary and generate their final key.
    for existing_dictionary in vbf_list:
        key_value = _build_existing_key(existing_dictionary)
        existing_keys.add(key_value)

    # Helper to unify dimension
    def _ensure_dimension_consistency(new_dimension):
        nonlocal existing_dimension
        if existing_dimension is None:
            existing_dimension = new_dimension
        else:
            if new_dimension != existing_dimension:
                raise click.ClickException(
                    f"New VBF dimension {new_dimension} does not match existing dimension {existing_dimension} in storage."
                )

    # -------------------------------------------------------------------------------
    # Adding new VBFs from inline --poly, --tt-file, --poly-file
    # -------------------------------------------------------------------------------
    new_vbfs = []

    # Univariate polynomials as lists of tuples: --poly as input. Require a single dimension from --dim.
    if poly:
        if dim_n is None:
            raise click.ClickException("Error: --dim is required when using the --poly option.")
        _ensure_dimension_consistency(dim_n)

        for poly_str in poly:
            try:
                poly_tuples = ast.literal_eval(poly_str)
            except Exception as parse_exc:
                click.echo(f"Error parsing user polynomial '{poly_str}': {parse_exc}", err=True)
                continue

            vbf_object = VBF(poly_tuples, dim_n, irr_poly)
            candidate_key = _build_key_from_vbf(vbf_object)
            if candidate_key in existing_keys:
                click.echo(f"Skipped duplicate polynomial {poly_str} (already in file).")
                continue

            new_vbfs.append(vbf_object)
            existing_keys.add(candidate_key)

    # The subsequent lines where each line is a Truth Table row.
    # Using concurrency for the Lagrange interpolation part.
    for tt_filepath_str in tt_file:
        lines_data, dim_n_val = _read_tt_file_firstline_n(tt_filepath_str)
        _ensure_dimension_consistency(dim_n_val)

        tasks_for_tt = [(idx, line_str, dim_n_val, irr_poly) for idx, line_str in enumerate(lines_data)]
        tt_results = [None]*len(tasks_for_tt)

        with concurrent.futures.ProcessPoolExecutor(max_workers=max_threads) as execpool:
            future_map = {}
            for tt_data in tasks_for_tt:
                tt_future = execpool.submit(_build_vbf_from_tt_worker, tt_data)
                future_map[tt_future] = tt_data[0]

            for done_future in concurrent.futures.as_completed(future_map):
                local_idx = future_map[done_future]
                try:
                    local_idx, built_object = done_future.result()
                    tt_results[local_idx] = built_object
                except Exception as exc:
                    click.echo(f"Error building VBF from TT index={local_idx} in '{tt_filepath_str}': {exc}", err=True)
                    tt_results[local_idx] = None

        # Filter out the None results.
        for idx_value, vbf_object in enumerate(tt_results):
            if vbf_object is None:
                continue
            if citation_all:
                vbf_object.invariants["citation"] = citation_all.strip()

            candidate_key = _build_key_from_vbf(vbf_object)
            if candidate_key in existing_keys:
                file_line_num = idx_value+2
                click.echo(f"Skipped duplicate truth table line {file_line_num} in '{tt_filepath_str}' (already in file).")
                continue

            new_vbfs.append(vbf_object)
            existing_keys.add(candidate_key)

    # Univariate polynomial-based files: --poly-file as input.
    for poly_path_str in poly_file:
        poly_lines, dim_value = _read_poly_file_firstline_n(poly_path_str)
        _ensure_dimension_consistency(dim_value)

        # The subsequent lines where each line is a univariate polynomial plus optional [citation].
        for line_no, line_text in enumerate(poly_lines, start=2):
            if not line_text.strip():
                continue

            if citation_all:
                # Override ALL bracketed citations.
                poly_part = line_text.split('[',1)[0].strip()
                bracketed_citation = citation_all.strip()
            else:
                poly_part, bracketed_citation = _extract_citation(line_text)

            try:
                poly_list_literal = _parse_line_to_univ_list_literal(poly_part)
                poly_data = ast.literal_eval(poly_list_literal)
            except Exception as exc:
                click.echo(f"Error building polynomial line {line_no} in '{poly_path_str}': {exc}", err=True)
                continue

            vbf_object = VBF(poly_data, dim_value, irr_poly)
            if bracketed_citation:
                vbf_object.invariants["citation"] = bracketed_citation

            candidate_key = _build_key_from_vbf(vbf_object)
            if candidate_key in existing_keys:
                click.echo(f"Skipped duplicate polynomial line {line_no} in '{poly_path_str}'.")
                continue

            new_vbfs.append(vbf_object)
            existing_keys.add(candidate_key)

    # If no new VBF(s), we are done.
    if not new_vbfs:
        click.echo("No new VBFs were added.")
        return
    
    # -------------------------------------------------------------------------------
    # Compute the differential uniformity and check if each new VBF is_apn (DU == 2).
    # -------------------------------------------------------------------------------
    aggregator_diff_uni = REG.get("invariant","diff_uni")
    tasks_for_new_vbfs = [(idx_val, vbf_object, aggregator_diff_uni) 
                          for idx_val, vbf_object in enumerate(new_vbfs)]
    results_map = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_threads) as execpool:
        future_list = []
        for single_task in tasks_for_new_vbfs:
            future = execpool.submit(_compute_diff_uni_aggregator_task, single_task)
            future_list.append(future)

        for done_future in concurrent.futures.as_completed(future_list):
            idx_value, updated_object = done_future.result()
            results_map[idx_value] = updated_object

    # We store all input functions.
    final_entries = []
    citation_idx = 0
    for idx_value in range(len(new_vbfs)):
        updated_vbf_object = results_map[idx_value]

        # Attach per-line citation.
        if citation_idx < len(citation):
            updated_vbf_object.invariants["citation"] = citation[citation_idx]
            citation_idx += 1

        if hasattr(updated_vbf_object.representation, "univariate_polynomial"):
            poly_list_data = updated_vbf_object.representation.univariate_polynomial
        else:
            poly_list_data = []

        cached_tt = updated_vbf_object._get_truth_table_list()

        final_entries.append({
            "poly": poly_list_data,
            "field_n": updated_vbf_object.field_n,
            "irr_poly": updated_vbf_object.irr_poly,
            "invariants": updated_vbf_object.invariants,
            "matches": [],
            "cached_tt": cached_tt
        })

    vbf_list.extend(final_entries)
    save_input_vbfs_and_matches(vbf_list)

    if final_entries:
        click.echo("\nNewly Added VBFs:")
        click.echo("-" * 100)
        for index_added, entry_dictionary in enumerate(final_entries, start=1):
            print_object = build_vbf_from_dict(entry_dictionary)
            click.echo(format_generic_vbf(print_object, f"VBF {index_added}"))
            click.echo("-" * 100)


def _compute_diff_uni_aggregator_task(task_data):
    # Concurrency worker for aggregator "diff_uni" and "is_apn".
    idx_value, vbf_object, aggregator_func = task_data
    aggregator_func(vbf_object)
    return (idx_value, vbf_object)


def _build_existing_key(vbf_dictionary):
    # Build existing key and use it to detect duplicates.
    vbf_object = build_vbf_from_dict(vbf_dictionary)
    return _build_key_from_vbf(vbf_object)


def _build_key_from_vbf(vbf_object):
    # To detect duplicates. Produces a JSON-based hash key.
    if hasattr(vbf_object.representation, "univariate_polynomial"):
        sorted_poly = sorted(
            vbf_object.representation.univariate_polynomial, key=lambda x: (x[0], x[1]))
        return json.dumps(["POLY", vbf_object.field_n, vbf_object.irr_poly, sorted_poly], sort_keys=True)
    else:
        # Truth Table-based.
        hasher = hashlib.sha256()
        tt_values = vbf_object._get_truth_table_list()
        for value in tt_values:
            hasher.update(value.to_bytes(4, 'little'))
        tt_hash = hasher.hexdigest()

        return json.dumps(["TT", vbf_object.field_n, vbf_object.irr_poly, tt_hash], sort_keys=True)


def _read_tt_file_firstline_n(filepath_str):
    file_path = Path(filepath_str)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {filepath_str}")

    # Returns entire file as a string.
    all_lines = file_path.read_text(encoding="utf-8").splitlines()
    all_lines = [ln.strip() for ln in all_lines if ln.strip()]

    if len(all_lines) < 2:
        raise ValueError(f"File '{filepath_str}' must have at least 2 lines => dimension + TTs.")

    try:
        dim_val = int(all_lines[0])
    except ValueError:
        raise ValueError(f"File '{filepath_str}': first line must be integer dimension.")
    
    return all_lines[1:], dim_val


def _read_poly_file_firstline_n(filepath_str):
    file_path = Path(filepath_str)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {filepath_str}")

    all_lines = file_path.read_text(encoding="utf-8").splitlines()
    all_lines = [ln.strip() for ln in all_lines if ln.strip()]

    if len(all_lines) < 2:
        raise ValueError(f"File '{filepath_str}' must have >= 2 lines => dimension + polynomials.")

    try:
        dim_val = int(all_lines[0])
    except ValueError:
        raise ValueError(f"File '{filepath_str}': first line must be integer dimension.")

    return all_lines[1:], dim_val


def _extract_citation(line_str):
    start_idx = line_str.rfind('[')
    end_idx = line_str.rfind(']')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        brack_cite = line_str[start_idx+1:end_idx].strip()
        poly_part = line_str[:start_idx].strip()
        return (poly_part, brack_cite)
    else:
        return (line_str,"")


def _parse_line_to_univ_list_literal(line_str: str) -> str:
    # Convert a string polynomial like 'g^15*x^48 + x^3' into a Python list literal: "[(15,48),(0,3)]".
    letter_holder = {"symbol": None} 

    terms = [term.strip() for term in line_str.split('+')]
    tuple_list = []

    for single_term in terms:
        coeff_exp, mon_exp = _parse_single_term(single_term, letter_holder)
        tuple_list.append((coeff_exp, mon_exp))

    # Build the final Python-list-literal string.
    return "[" + ",".join(f"({coeff},{mon})" for (coeff, mon) in tuple_list) + "]"


def _parse_single_term(term_str: str, letter_holder: dict) -> (int, int):
    term_str = term_str.strip()

    if term_str.endswith(','):
        term_str = term_str[:-1].strip()
    
    if term_str == '1':
        # coefficient_exp=0, monomial_exp=0 = 1.
        return (0, 0)
    
    if '*' in term_str:
        parts = [part.strip() for part in term_str.split('*')]
        if len(parts) != 2:
            raise ValueError(f"Unrecognized polynomial term '{term_str}'.")
        coeff_segment, mon_segment = parts
        coeff_exp = _parse_coefficient(coeff_segment, letter_holder)
        mon_exp = _parse_monomial(mon_segment)
        return (coeff_exp, mon_exp)
    else:
        # Just a single coefficient, or just a single monomial.
        if term_str.startswith('x'):
            mon_exp = _parse_monomial(term_str)
            return (0, mon_exp)
        else:
            coeff_exp = _parse_coefficient(term_str, letter_holder)
            return (coeff_exp, 0)


def _parse_coefficient(coeff_segment: str, letter_holder: dict) -> int:
    # Coefficient format: 'g' = 1, 'g^77' = 77.
    coeff_segment = coeff_segment.strip().lower()

    match = re.match(r'^([a-z])(\^\d+)?$', coeff_segment)
    if not match:
        raise ValueError(f"Unrecognized coefficient '{coeff_segment}'. Expected 'g' or 'g^<int>'.")

    letter_part = match.group(1)
    exponent_part = match.group(2)

    if letter_holder["symbol"] is None:
        letter_holder["symbol"] = letter_part
    else:
        if letter_holder["symbol"] != letter_part:
            raise ValueError(
                f"Coefficient '{letter_holder['symbol']}' and '{letter_part}' in the same polynomial.")

    if exponent_part is None:
        return 1

    exponent_str = exponent_part[1:]
    if not exponent_str.isdigit():
        raise ValueError(f"Unrecognized exponent in '{coeff_segment}'. Must be an integer.")
    return int(exponent_str)


def _parse_monomial(mon_segment: str) -> int:
    # Monomial format: 'x' = 1, 'x^77' = 77.
    mon_segment = mon_segment.strip().lower()
    if mon_segment == 'x':
        return 1
    if mon_segment.startswith('x^'):
        exponent_str = mon_segment[2:].strip()
        if not exponent_str.isdigit():
            raise ValueError(f"Unrecognized monomial '{mon_segment}'. Expected 'x^<int>'.")
        return int(exponent_str)
    raise ValueError(f"Unrecognized monomial '{mon_segment}'. Expected 'x' or 'x^<int>'.")


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
    

def _build_vbf_from_tt_worker(task_data):
    # Worker function for concurrency: Truth table -> Lagrange interpolation -> VBF object.
    line_index, tt_line, dim_value_line, user_irr_poly = task_data
    parsed_tt_values = _parse_tt_values(tt_line)
    if parsed_tt_values is None:
        raise ValueError(f"Could not parse truth table line: {tt_line}")
    if len(parsed_tt_values) != (1 << dim_value_line):
        raise ValueError(f"Truth table length mismatch for line: {tt_line}")

    tt_representation = TruthTableRepresentation(parsed_tt_values)
    vbf_object = VBF.from_representation(tt_representation, dim_value_line, user_irr_poly)
    return (line_index, vbf_object)