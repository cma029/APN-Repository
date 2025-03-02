import os
import pandas as pd
import json
from typing import List, Dict, Any, Tuple
from apn_object import APN
from apn_invariants import compute_all_invariants


def get_parquet_filename(field_dimension: int) -> str:
    # Returns the filename for storing APNs of field dimension n. E.g., for n=6 -> 'apn_data_6.parquet'.
    return f"apn_data_{field_dimension}.parquet"


def is_duplicate_candidate(
    dataframe: pd.DataFrame,
    field_dimension: int,
    irreducible_poly: str,
    polynomial_terms: List[Tuple[int,int]]
) -> bool:
    # Check if (field_n, irr_poly, sorted poly) is already in the dataframe.
    sorted_candidate = sorted(polynomial_terms, key=lambda term: (term[0], term[1]))
    matching_rows = dataframe[
        (dataframe["field_n"] == field_dimension) &
        (dataframe["irr_poly"] == irreducible_poly)
    ]
    if matching_rows.empty:
        return False

    for _, row in matching_rows.iterrows():
        poly_str = row["poly"]
        if not poly_str:
            continue
        try:
            existing_poly = json.loads(poly_str)
            existing_sorted = sorted(existing_poly, key=lambda t: (t[0], t[1]))
            if existing_sorted == sorted_candidate:
                return True
        except:
            pass

    return False


# --------------------------------------------------------------
# READING AND WRITING FILES
# --------------------------------------------------------------

def load_apn_dataframe_for_field(field_dimension: int) -> pd.DataFrame:
    """
    Loads all APNs for field degree n from the Parquet file.
    If no file exists, returns an empty DataFrame with required columns.
    """
    filename = get_parquet_filename(field_dimension)
    if not os.path.isfile(filename):
        columns = [
            "field_n", "poly", "irr_poly",
            "odds", "odws",
            "delta_rank", "gamma_rank",
            "algebraic_degree", "is_quadratic",
            "is_apn", "is_monomial",
            "k_to_1", "citation"
        ]
        return pd.DataFrame(columns=columns)

    try:
        dataframe = pd.read_parquet(filename)

        needed_cols = [
            "field_n", "poly", "irr_poly",
            "odds", "odws",
            "delta_rank", "gamma_rank",
            "algebraic_degree", "is_quadratic",
            "is_apn", "is_monomial",
            "k_to_1", "citation"
        ]
        for colname in needed_cols:
            if colname not in dataframe.columns:
                dataframe[colname] = None

        return dataframe
    except Exception as read_error:
        print(f"Error reading {filename}: {read_error}")
        columns = [
            "field_n", "poly", "irr_poly",
            "odds", "odws",
            "delta_rank", "gamma_rank",
            "algebraic_degree", "is_quadratic",
            "is_apn", "is_monomial",
            "k_to_1", "citation"
        ]
        return pd.DataFrame(columns=columns)


def save_apn_dataframe_for_field(field_dimension: int, dataframe: pd.DataFrame) -> None:
    # Writes dataframe to apn_data_{field_dimension}.parquet with Snappy compression.
    filename = get_parquet_filename(field_dimension)
    try:
        dataframe.to_parquet(filename, index=False, compression='snappy')
        print(f"Data successfully written to {filename} with Snappy compression.")
    except Exception as write_error:
        print(f"Error writing to {filename}: {write_error}")


# --------------------------------------------------------------
# STORING A NEW APN
# --------------------------------------------------------------

def store_apn_pandas(polynomial_terms: List[Tuple[int, int]], field_dimension: int, irreducible_polynomial: str,
    citation_message: str = "No citation provided.") -> None:
    """
    Build an APN from polynomial terms, compute invariants, and store it as a new row
    in the Parquet database for the specified field dimension.
    """
    try:
        apn_object = APN(polynomial_terms, field_dimension, irreducible_polynomial)
    except Exception as parse_err:
        print(f"Error constructing APN from polynomial {polynomial_terms} => {parse_err}")
        return

    # Load the existing database.
    df_existing = load_apn_dataframe_for_field(field_dimension)
    if is_duplicate_candidate(df_existing, field_dimension, irreducible_polynomial, polynomial_terms):
        print(f"APN {polynomial_terms} is a duplicate. Will not be stored.")
        return

    compute_all_invariants(apn_object)

    if not apn_object.invariants.get("is_apn", False):
        print("The APN is not an APN (differential uniformity != 2). Will not be stored.")
        return

    # Convert numeric invariants to the correct type.
    delta_rank_val = apn_object.invariants.get("delta_rank", None)
    if delta_rank_val is not None:
        delta_rank_val = int(delta_rank_val)

    gamma_rank_val = apn_object.invariants.get("gamma_rank", None)
    if gamma_rank_val is not None:
        gamma_rank_val = int(gamma_rank_val)

    algebraic_deg_val = apn_object.invariants.get("algebraic_degree", None)
    if algebraic_deg_val is not None:
        algebraic_deg_val = int(algebraic_deg_val)

    # Boolean columns.
    is_quad_val = bool(apn_object.invariants.get("is_quadratic", False))
    is_apn_val  = bool(apn_object.invariants.get("is_apn", False))
    is_mono_val = bool(apn_object.invariants.get("is_monomial", False))

    # Convert ODDS/ODWS if they're dictionaries to store as JSON.
    odds_val = apn_object.invariants.get("odds", "non-quadratic")
    if isinstance(odds_val, dict):
        odds_val = json.dumps(odds_val)

    odws_val = apn_object.invariants.get("odws", "non-quadratic")
    if isinstance(odws_val, dict):
        odws_val = json.dumps(odws_val)

    kto1_val = apn_object.invariants.get("k_to_1", "unknown")
    citation_val = apn_object.invariants.get("citation", citation_message)

    row_dict = {
        "field_n": int(field_dimension),
        "poly": json.dumps(polynomial_terms),
        "irr_poly": irreducible_polynomial,

        "odds": odds_val,
        "odws": odws_val,
        "delta_rank": delta_rank_val,
        "gamma_rank": gamma_rank_val,
        "algebraic_degree": algebraic_deg_val,
        "is_quadratic": is_quad_val,
        "is_apn": is_apn_val,
        "is_monomial": is_mono_val,
        "k_to_1": str(kto1_val),
        "citation": str(citation_val)
    }

    # Append & save.
    new_df = pd.DataFrame([row_dict])
    df_combined = pd.concat([df_existing, new_df], ignore_index=True)
    save_apn_dataframe_for_field(field_dimension, df_combined)
    print(f"APN {polynomial_terms} saved => done.")


# --------------------------------------------------------------
# LOADING + RECONSTRUCTING APN OBJECTS
# --------------------------------------------------------------

def load_apn_objects_for_field_pandas(field_dimension: int) -> List[APN]:
    """
    Loads all APN entries for field degree n from the Parquet file, reconstructs APN objects,
    and populates their invariants with ODDS/ODWS data, ranks and invariants.
    """
    df_loaded = load_apn_dataframe_for_field(field_dimension)
    if df_loaded.empty:
        print(f"No APNs found in database for field_n={field_dimension}.")
        return []

    apn_list: List[APN] = []

    for index, row in df_loaded.iterrows():
        try:
            # Parse polynomial from the stored JSON.
            polynomial_json_string = row.get("poly", "")
            polynomial_data = []
            if polynomial_json_string:
                try:
                    polynomial_data = json.loads(polynomial_json_string)
                except:
                    polynomial_data = []

            field_n_val  = int(row.get("field_n", field_dimension))
            irr_poly_val = row.get("irr_poly", "")

            # Build an APN object directly.
            apn_obj = APN(polynomial_data, field_n_val, irr_poly_val)
            if not hasattr(apn_obj, "invariants"):
                apn_obj.invariants = {}

            # Reconstruct ODDS if it's JSON.
            odds_column_value = row.get("odds", "non-quadratic")
            if isinstance(odds_column_value, str):
                if odds_column_value == "non-quadratic":
                    apn_obj.invariants["odds"] = "non-quadratic"
                else:
                    try:
                        parsed_odds = json.loads(odds_column_value)
                        if isinstance(parsed_odds, dict):
                            odds_dict = {}
                            for key, val in parsed_odds.items():
                                odds_dict[int(key)] = int(val)
                            apn_obj.invariants["odds"] = odds_dict
                        else:
                            apn_obj.invariants["odds"] = parsed_odds
                    except:
                        apn_obj.invariants["odds"] = "non-quadratic"
            else:
                apn_obj.invariants["odds"] = odds_column_value

            # Reconstruct ODWS if it's JSON.
            odws_column_value = row.get("odws", "non-quadratic")
            if isinstance(odws_column_value, str):
                if odws_column_value == "non-quadratic":
                    apn_obj.invariants["odws"] = "non-quadratic"
                else:
                    try:
                        parsed_odws = json.loads(odws_column_value)
                        if isinstance(parsed_odws, dict):
                            odws_dict = {}
                            for key, val in parsed_odws.items():
                                odws_dict[int(key)] = int(val)
                            apn_obj.invariants["odws"] = odws_dict
                        else:
                            apn_obj.invariants["odws"] = parsed_odws
                    except:
                        apn_obj.invariants["odws"] = "non-quadratic"
            else:
                apn_obj.invariants["odws"] = odws_column_value

            # Numeric columns.
            delta_rank_value = row.get("delta_rank", None)
            if pd.notna(delta_rank_value):
                apn_obj.invariants["delta_rank"] = int(delta_rank_value)

            gamma_rank_value = row.get("gamma_rank", None)
            if pd.notna(gamma_rank_value):
                apn_obj.invariants["gamma_rank"] = int(gamma_rank_value)

            algebraic_degree_value = row.get("algebraic_degree", None)
            if pd.notna(algebraic_degree_value):
                apn_obj.invariants["algebraic_degree"] = int(algebraic_degree_value)

            # Boolean columns.
            apn_obj.invariants["is_quadratic"] = bool(row.get("is_quadratic", False))
            apn_obj.invariants["is_apn"]       = bool(row.get("is_apn", False))
            apn_obj.invariants["is_monomial"]  = bool(row.get("is_monomial", False))

            # k_to_1 column.
            apn_obj.invariants["k_to_1"] = row.get("k_to_1","unknown")

            # Citation
            citation_value = row.get("citation","")
            apn_obj.invariants["citation"] = citation_value if pd.notna(citation_value) else ""

            apn_list.append(apn_obj)

        except Exception as reconstruct_error:
            print(f"Error building APN from row {index}: {reconstruct_error}")

    return apn_list