import concurrent.futures
from collections import defaultdict
from typing import Callable, List, Dict, Any, Tuple, Union
from storage.json_storage_utils import (
    load_equivalence_list,
    save_equivalence_list
)
from cli_commands.cli_utils import polynomial_to_str


def run_equivalence_on_matches(input_apn_list: List[Dict[str, Any]], concurrency_tasks: List[Tuple[int, int, Any]],
                               equivalence_worker_fn: Callable[..., Union[bool, None]], eq_type_str: str,
                               max_workers: int = None) -> List[Dict[str, Any]]:
    # Runs the concurrency-based equivalence checks for a single equivalence algorithm.

    # If no tasks, nothing to do.
    if not concurrency_tasks:
        return input_apn_list

    # Run concurrency.
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        task_to_indices_map = {}
        for task_data in concurrency_tasks:
            # The first two items in each task_data are (apn_idx, match_idx).
            apn_idx, match_idx = task_data[0], task_data[1]
            fut = executor.submit(equivalence_worker_fn, task_data)
            task_to_indices_map[fut] = (apn_idx, match_idx)

        for done_task in concurrent.futures.as_completed(task_to_indices_map):
            (the_apn_idx, the_match_idx) = task_to_indices_map[done_task]
            result_val = done_task.result()  # True / False / None
            results.append((the_apn_idx, the_match_idx, result_val))

    # Organize concurrency results by input APN index.
    equivalence_map = defaultdict(list)
    for (apn_i, match_i, eq_val) in results:
        equivalence_map[apn_i].append((match_i, eq_val))

    removed_apn_indices = set()
    non_equivalent_matches_map = defaultdict(list)

    # For each APN that has a True match we remove the entire APN from the list.
    for apn_idx, pair_list in equivalence_map.items():
        any_equivalent = [(m_idx, True) for (m_idx, val) in pair_list if val is True]
        if any_equivalent:
            # Record the first True match in equivalence_list.json.
            chosen_m = any_equivalent[0][0]
            input_apn_dict = input_apn_list[apn_idx]
            matched_apn_dict = input_apn_dict["matches"][chosen_m]
            _store_equivalence_record(input_apn_dict, matched_apn_dict, eq_type_str)
            removed_apn_indices.add(apn_idx)
        else:
            # If none are True we remove only those that are definitively False.
            failed_match_indexes = [m_idx for (m_idx, val) in pair_list if val is False]
            non_equivalent_matches_map[apn_idx].extend(failed_match_indexes)

    # Build a new list excluding fully removed APNs.
    filtered_apn_list = []
    for i, apn_dict in enumerate(input_apn_list):
        if i not in removed_apn_indices:
            filtered_apn_list.append(apn_dict)

    # For the remaining APNs, remove only their False matches.
    for i, apn_dict in enumerate(input_apn_list):
        if i in removed_apn_indices:
            continue
        fails = non_equivalent_matches_map.get(i, [])
        if fails:
            old_matches = apn_dict.get("matches", [])
            new_matches = [
                m_dict for idx_m, m_dict in enumerate(old_matches)
                if idx_m not in fails
            ]
            apn_dict["matches"] = new_matches

    # Return the final updated list.
    return filtered_apn_list


def _store_equivalence_record(input_apn_dict: Dict[str, Any], matched_apn_dict: Dict[str, Any],
                              eq_type: str) -> None:
    # Store a record of the found equivalence in equivalence_list.json.
    poly_str = polynomial_to_str(input_apn_dict["poly"])
    match_poly_str = polynomial_to_str(matched_apn_dict["poly"])

    eq_list = load_equivalence_list()
    eq_list.append({
        "eq_type": eq_type,
        "input_apn": {
            "poly": input_apn_dict["poly"],
            "poly_str": poly_str,
            "field_n": input_apn_dict["field_n"],
            "irr_poly": input_apn_dict["irr_poly"],
            "invariants": input_apn_dict.get("invariants", {})
        },
        "matched_apn": {
            "poly": matched_apn_dict["poly"],
            "poly_str": match_poly_str,
            "field_n": matched_apn_dict["field_n"],
            "irr_poly": matched_apn_dict["irr_poly"],
            "invariants": matched_apn_dict.get("invariants", {})
        }
    })
    save_equivalence_list(eq_list)