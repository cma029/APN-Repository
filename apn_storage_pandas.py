import os
import pandas as pd
import json
from typing import List, Dict, Any, Tuple
import concurrent.futures
import multiprocessing

from c_spectra_bindings import (
    vbf_tt_differential_spectrum_python,
    vbf_tt_extended_walsh_spectrum_python
)
from computations.rank.delta_rank import DeltaRankComputation
from computations.rank.gamma_rank import GammaRankComputation
from user_input_parser import PolynomialParser
from apn_object import APN
# from apn_test import DifferentialUniformityComputer
# from apn_is_quadratic import is_quadratic_apn


def get_parquet_filename(field_dimension: int) -> str:
    # Returns the filename for storing APNs of field dimension n. E.g., for n=6 -> 'apn_data_6.parquet'.
    return f"apn_data_{field_dimension}.parquet"

def poly_to_key(polynomial_terms: List[Tuple[int, int]]) -> str:
    # Converts a polynomial list [(coeff_exp, mon_exp), ...] into a canonical JSON
    # string for duplicate-checking by sorting the terms.
    sorted_polynomial = sorted(polynomial_terms, key=lambda t: (t[0], t[1]))
    return json.dumps(sorted_polynomial)


# --------------------------------------------------------------
# READING AND WRITING FILES
# --------------------------------------------------------------

def load_apn_df_for_field(field_dimension: int) -> pd.DataFrame:
    # Loads all APNs for field degree n from the Parquet file.
    # If no file exists, returns an empty DataFrame with the specified columns.
    filename = get_parquet_filename(field_dimension)
    if not os.path.isfile(filename):
        columns = [
            "field_n", "irr_poly", "poly_key", "poly",
            "odds_str", "odws_str", "gamma_rank", "delta_rank", "citation"
        ]
        return pd.DataFrame(columns=columns)
    try:
        return pd.read_parquet(filename)
    except Exception as error:
        print(f"Error reading {filename}: {error}")
        # Return empty DataFrame to avoid crashes
        columns = [
            "field_n", "irr_poly", "poly_key", "poly",
            "odds_str", "odws_str", "gamma_rank", "delta_rank", "citation"
        ]
        return pd.DataFrame(columns=columns)


def save_apn_df_for_field(field_dimension: int, dataframe: pd.DataFrame) -> None:
    # Overwrites the Parquet file for field degree n with the given DataFrame.
    filename = get_parquet_filename(field_dimension)
    try:
        dataframe.to_parquet(filename, index=False, compression='snappy')
        print(f"Data successfully written to {filename} with Snappy compression.")
    except Exception as error:
        print(f"Error writing to {filename}: {error}")


# --------------------------------------------------------------
# STORING A NEW APN
# --------------------------------------------------------------

def store_apn_pandas(
    polynomial_terms: List[Tuple[int, int]],
    field_dimension: int,
    irreducible_polynomial: str,
    citation_message: str = "No citation provided."
) -> None:

    # Initialize PolynomialParser and parse the polynomial into an APN object.
    parser = PolynomialParser()
    try:
        apn_object = parser.parse_univariate_polynomial(polynomial_terms, field_dimension, irreducible_polynomial)
    except Exception as parse_error:
        print(f"Error parsing polynomial {polynomial_terms} for field_n={field_dimension}: {parse_error}")
        return

    # Ensure apn_object.invariants dict
    if not hasattr(apn_object, "invariants"):
        apn_object.invariants = {}

    """
    # Check if the APN is valid (differential uniformity == 2).
    try:
        differential_uniformity_computer = DifferentialUniformityComputer()
        differential_uniformity_value = differential_uniformity_computer.compute_du(apn_object)
        is_apn_value = (differential_uniformity_value == 2)
    except Exception as du_error:
        print(f"Error computing differential uniformity for {polynomial_terms}: {du_error}")
        is_apn_value = False

    if not is_apn_value:
        print(f"APN {polynomial_terms} is not valid (differential_uniformity != 2); skipping storage.")
        return
    apn_object.invariants["is_apn"] = True

    # Check if the APN is quadratic.
    try:
        truth_table_representation = apn_object.get_truth_table()
        truth_list = truth_table_representation.representation.truth_table
        is_quadratic_value = is_quadratic_apn(truth_list, field_dimension)
    except Exception as quad_error:
        print(f"Error checking is_quadratic for {polynomial_terms}: {quad_error}")
        is_quadratic_value = False

    apn_object.invariants["is_quadratic"] = is_quadratic_value
    """
    # Compute Gamma and Delta ranks using multi-threading (and OD spectra if is_quadratic is True).
    number_of_workers = multiprocessing.cpu_count()
    gamma_task = None
    delta_task = None
    odds_task = None
    odws_task = None

    # If we have not defined is_quadratic_value yet, default to False for the concurrency snippet:
    is_quadratic_value = apn_object.invariants.get("is_quadratic", False)

    # Concurrency with process-based executor.
    with concurrent.futures.ThreadPoolExecutor(max_workers=number_of_workers) as executor:
        gamma_task = executor.submit(_compute_and_store_gamma_rank, apn_object)
        delta_task = executor.submit(_compute_and_store_delta_rank, apn_object)

        # If APN is quadratic, also compute ODDS and ODWS.
        if is_quadratic_value:
            odds_task = executor.submit(_compute_and_store_odds, apn_object)
            odws_task = executor.submit(_compute_and_store_odws, apn_object)

        rank_and_spectrum_tasks = [gamma_task, delta_task]
        if odds_task:
            rank_and_spectrum_tasks.append(odds_task)
        if odws_task:
            rank_and_spectrum_tasks.append(odws_task)

        concurrent.futures.wait(rank_and_spectrum_tasks)

    gamma_rank_value = apn_object.invariants.get("gamma_rank")
    delta_rank_value = apn_object.invariants.get("delta_rank")
    odds_value = apn_object.invariants.get("odds", "non-quadratic")
    odws_value = apn_object.invariants.get("odws", "non-quadratic")

    if isinstance(odds_value, dict):
        odds_str = json.dumps(odds_value)
    else:
        odds_str = "Non-quadratic"

    if isinstance(odws_value, dict):
        odws_str = json.dumps(odws_value)
    else:
        odws_str = "Non-quadratic"

    # DataFrame.
    poly_key_string = poly_to_key(polynomial_terms)
    new_apn_row = {
        "field_n": field_dimension,
        "irr_poly": irreducible_polynomial,
        "poly_key": poly_key_string,
        "poly": json.dumps(polynomial_terms),
        "odds_str": odds_str,
        "odws_str": odws_str,
        "gamma_rank": gamma_rank_value,
        "delta_rank": delta_rank_value,
        "citation": citation_message
    }

    # Check for duplicates, append, save.
    df_existing = load_apn_df_for_field(field_dimension)
    duplicate_filter = (
        (df_existing["field_n"] == field_dimension) &
        (df_existing["irr_poly"] == irreducible_polynomial) &
        (df_existing["poly_key"] == poly_key_string)
    )
    if not df_existing[duplicate_filter].empty:
        print(f"APN {polynomial_terms} already exists in apn_data_{field_dimension}.parquet; skipping.")
        return

    new_df = pd.DataFrame([new_apn_row])
    try:
        df_combined = pd.concat([df_existing, new_df], ignore_index=True)
    except Exception as concat_error:
        print(f"Error appending new APN to DataFrame: {concat_error}")
        return

    save_apn_df_for_field(field_dimension, df_combined)
    print(f"APN {polynomial_terms} successfully added to apn_data_{field_dimension}.parquet.")


# --------------------------------------------------------------
# LOADING + RECONSTRUCTING APN OBJECTS
# --------------------------------------------------------------

def load_apn_objects_for_field_pandas(field_dimension: int) -> List[APN]:
    # Loads all APN entries for field degree n from the Parquet file, reconstructs APN objects,
    # and populates their invariants with ODDS/ODWS data and ranks and more.
    df_loaded = load_apn_df_for_field(field_dimension)
    if df_loaded.empty:
        print(f"No APNs found for field_n={field_dimension}.")
        return []

    apn_list = []
    parser = PolynomialParser()

    for index, row in df_loaded.iterrows():
        try:
            # Handle "poly" (skip if empty or not valid JSON).
            polynomial_json_string = row["poly"]
            if not polynomial_json_string or polynomial_json_string.strip() == "":
                print(f"Error reconstructing APN at index {index}: 'poly' is empty. Skipping row.")
                continue
            try:
                polynomial_data = json.loads(polynomial_json_string)
            except json.JSONDecodeError:
                print(f"Error reconstructing APN at index {index}: invalid JSON in 'poly'. Skipping row.")
                continue

            apn_object = parser.parse_univariate_polynomial(polynomial_data, field_dimension, row["irr_poly"])
            if not hasattr(apn_object, "invariants"):
                apn_object.invariants = {}

            odds_column_value = row.get("odds_str", "non-quadratic")
            odws_column_value = row.get("odws_str", "non-quadratic")

            # Try to parse them if they aren't "non-quadratic".
            if pd.notna(odds_column_value) and odds_column_value != "non-quadratic":
                try:
                    loaded_odds_dict = json.loads(odds_column_value)
                    loaded_odds_dict = {int(k): int(v) for k, v in loaded_odds_dict.items()}
                    apn_object.invariants["odds"] = loaded_odds_dict
                except json.JSONDecodeError:
                    print(f"Warning: 'odds_str' at index {index} not valid JSON. Setting to 'non-quadratic'.")
                    apn_object.invariants["odds"] = "non-quadratic"
            else:
                apn_object.invariants["odds"] = "non-quadratic"

            if pd.notna(odws_column_value) and odws_column_value != "non-quadratic":
                try:
                    loaded_odws_dict = json.loads(odws_column_value)
                    loaded_odws_dict = {int(k): int(v) for k, v in loaded_odws_dict.items()}
                    apn_object.invariants["odws"] = loaded_odws_dict
                except json.JSONDecodeError:
                    print(f"Warning: 'odws_str' at index {index} not valid JSON. Setting to 'non-quadratic'.")
                    apn_object.invariants["odws"] = "non-quadratic"
            else:
                apn_object.invariants["odws"] = "non-quadratic"

            # Load gamma_rank & delta_rank & citation.
            gamma_rank_value = row["gamma_rank"]
            apn_object.invariants["gamma_rank"] = gamma_rank_value if pd.notna(gamma_rank_value) else None

            delta_rank_value = row["delta_rank"]
            apn_object.invariants["delta_rank"] = delta_rank_value if pd.notna(delta_rank_value) else None

            citation_value = row["citation"]
            apn_object.invariants["citation"] = citation_value if pd.notna(citation_value) else ""

            apn_list.append(apn_object)

        except Exception as reconstruct_error:
            # Catch any unexpected error per row (to avoid crashing the entire load).
            print(f"Error reconstructing APN at index {index}: {reconstruct_error}")
            continue

    return apn_list


# Helper concurrency methods for store_apn_pandas
def _compute_and_store_gamma_rank(apn_object: APN):
    if "gamma_rank" not in apn_object.invariants:
        try:
            gamma_computation = GammaRankComputation()
            rank_value = gamma_computation.compute_rank(apn_object)
            apn_object.invariants["gamma_rank"] = rank_value
        except Exception as error:
            print(f"Error computing gamma rank: {error}")
            apn_object.invariants["gamma_rank"] = None


def _compute_and_store_delta_rank(apn_object: APN):
    if "delta_rank" not in apn_object.invariants:
        try:
            delta_computation = DeltaRankComputation()
            rank_value = delta_computation.compute_rank(apn_object)
            apn_object.invariants["delta_rank"] = rank_value
        except Exception as error:
            print(f"Error computing delta rank: {error}")
            apn_object.invariants["delta_rank"] = None


def _compute_and_store_odds(apn_object: APN):
    if "odds" in apn_object.invariants:
        return

    is_quad = apn_object.invariants.get("is_quadratic", False)
    if is_quad:
        try:
            truth_table_list = apn_object._get_truth_table_list()
            dimension = apn_object.field_n
            odds_result = vbf_tt_differential_spectrum_python(truth_table_list, dimension)
            apn_object.invariants["odds"] = {int(key): int(val) for key, val in odds_result.items()}
        except Exception as error:
            print(f"Error computing the Ortho-Derivative Differential Spectrum: {error}")
            apn_object.invariants["odds"] = "non-quadratic"
    else:
        apn_object.invariants.setdefault("odds", "non-quadratic")


def _compute_and_store_odws(apn_object: APN):
    if "odws" in apn_object.invariants:
        return

    is_quad = apn_object.invariants.get("is_quadratic", False)
    if is_quad:
        try:
            truth_table_list = apn_object._get_truth_table_list()
            dimension = apn_object.field_n
            odws_result = vbf_tt_extended_walsh_spectrum_python(truth_table_list, dimension)
            apn_object.invariants["odws"] = {int(key): int(val) for key, val in odws_result.items()}
        except Exception as error:
            print(f"Error computing the Ortho-Derivative extended Walsh Spectrum: {error}")
            apn_object.invariants["odws"] = "non-quadratic"
    else:
        apn_object.invariants.setdefault("odws", "non-quadratic")