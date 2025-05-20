from __future__ import annotations
import concurrent.futures
from collections import defaultdict
from typing import Any, Dict, List, Tuple
from cli_commands.cli_utils import polynomial_to_str
from storage.json_storage_utils import load_equivalence_list, save_equivalence_list
from registry import REG


def _equivalence_worker(task_data: Tuple[int, int, Any, Any, str]) -> Tuple[int, int, bool | None]:
    """
    The concurrency worker function, receives: (vbf_index, match_index, object_F, object_G, eq_key).
    Returns: (vbf_index, match_index, bool or None).
    """
    vbf_index, match_index, object_F, object_G, eq_key = task_data
    try:
        eq_class = REG.get("equivalence", eq_key)
        result_bool = eq_class().are_equivalent(object_F, object_G)
        return vbf_index, match_index, bool(result_bool)
    except Exception as exc:
        print(f"[equiv-worker] {eq_key} failed:", exc)
        return vbf_index, match_index, None


def run_equivalence_on_matches(*,input_vbf_list: List[Dict[str, Any]], concurrency_tasks: List[Tuple[int, int, Any]], 
                               eq_key: str, max_workers: int | None = None) -> List[Dict[str, Any]]:
    # Runs concurrency-based equivalence checks (CCZ, 3to1, etc.) for a single equivalence algorithm.
    if not concurrency_tasks:
        return input_vbf_list

    # Wrap each concurrency task with eq_key so the worker can fetch the right class.
    packaged_tasks = []
    for (vbf_idx, match_idx, vbfF, vbfG) in concurrency_tasks:
        packaged_tasks.append((vbf_idx, match_idx, vbfF, vbfG, eq_key))

    # -------------------------------------------------------------------
    # Run concurrency.
    # -------------------------------------------------------------------
    results: List[Tuple[int, int, bool | None]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_equivalence_worker, task_item): (task_item[0], task_item[1])
            for task_item in packaged_tasks
        }
        for done_future in concurrent.futures.as_completed(future_map):
            input_vbf_idx, match_vbf_idx = future_map[done_future]
            try:
                _, _, worker_result = done_future.result()  # True / False / None.
            except Exception:
                worker_result = None
            results.append((input_vbf_idx, match_vbf_idx, worker_result))

    # Organize concurrency results by input VBF index.
    equivalence_map: Dict[int, List[Tuple[int, bool | None]]] = defaultdict(list)
    for (vbf_i, match_i, eq_val) in results:
        equivalence_map[vbf_i].append((match_i, eq_val))

    remove_entire_vbfs: set[int] = set()
    inequivalent_matches_map: Dict[int, List[int]] = defaultdict(list)

    # For each APN that has a True match we remove the entire APN from the list.
    for single_vbf_index, pair_list in equivalence_map.items():
        any_equivalent = [m_idx for (m_idx, val) in pair_list if val is True]
        if any_equivalent:
            # Record the first True match in equivalence_list.json.
            _store_equivalence_record(input_vbf_list[single_vbf_index],
                input_vbf_list[single_vbf_index]["matches"][any_equivalent[0]], eq_key)
            remove_entire_vbfs.add(single_vbf_index)
        else:
            # If none are True, we only remove those that are definitively False.
            inequivalent = [m_idx for (m_idx, val) in pair_list if val is False]
            inequivalent_matches_map[single_vbf_index] = inequivalent

    # Build a new list of VBFs, excluding those that are removed.
    filtered_vbf_list: List[Dict[str, Any]] = []
    for idx, vbf_dictionary in enumerate(input_vbf_list):
        if idx in remove_entire_vbfs:
            continue

        inequivalent_for_this_vbf = set(inequivalent_matches_map.get(idx, []))
        old_matches = vbf_dictionary.get("matches", [])
        new_matches = [
            match_dict
            for match_idx, match_dict in enumerate(old_matches)
            if match_idx not in inequivalent_for_this_vbf
        ]
        vbf_dictionary["matches"] = new_matches

        # If new_matches is now empty, we set no_more_matches = True.
        if not new_matches:
            vbf_dictionary["no_more_matches"] = True

        filtered_vbf_list.append(vbf_dictionary)

    # Return the final updated list.
    return filtered_vbf_list


def _store_equivalence_record(input_vbf_dictionary: Dict[str, Any], matched_vbf_dictionary: Dict[str, Any],
                              eq_type_string: str) -> None:
    # Store a record of the discovered equivalence in equivalence_list.json.
    equivalence_list = load_equivalence_list()

    equivalence_list.append(
        {
            "eq_type": eq_type_string,
            "input_vbf": {
                "poly": input_vbf_dictionary["poly"],
                "poly_str": polynomial_to_str(input_vbf_dictionary["poly"]),
                "field_n": input_vbf_dictionary["field_n"],
                "irr_poly": input_vbf_dictionary["irr_poly"],
                "invariants": input_vbf_dictionary.get("invariants", {}),
            },
            "matched_vbf": {
                "poly": matched_vbf_dictionary["poly"],
                "poly_str": polynomial_to_str(matched_vbf_dictionary["poly"]),
                "field_n": matched_vbf_dictionary["field_n"],
                "irr_poly": matched_vbf_dictionary["irr_poly"],
                "invariants": matched_vbf_dictionary.get("invariants", {}),
            },
        }
    )
    save_equivalence_list(equivalence_list)