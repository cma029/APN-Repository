import os
import pandas as pd
import json
from typing import List, Tuple
from apn_object import APN
from apn_invariants import compute_all_invariants


def get_parquet_filename(field_dimension: int) -> str:
    # Returns the filename for storing APNs of field dimension n. E.g., for n=6 -> 'apn_data_6.parquet'.
    return f"apn_data_{field_dimension}.parquet"


def is_duplicate_candidate(dataframe: pd.DataFrame, field_dimension: int, 
    irreducible_poly: str, polynomial_terms: List[Tuple[int,int]]) -> bool:
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
# STORING A NEW APN FUNCTION
# --------------------------------------------------------------

def store_apn_pandas(polynomial_terms: List[Tuple[int, int]], field_dimension: int, irreducible_polynomial: str,
    citation_message: str = "No citation provided.") -> None:
    """
    Build an APN object from polynomial terms, compute invariants, and store the object 
    as a new row in the Parquet database for the specified field dimension.
    """
    try:
        apn_object = APN(polynomial_terms, field_dimension, irreducible_polynomial)
    except Exception as parse_err:
        print(f"Error constructing APN from polynomial {polynomial_terms} => {parse_err}")
        return

    # Load the existing database.
    existing_dataframe = load_apn_dataframe_for_field(field_dimension)
    if is_duplicate_candidate(existing_dataframe, field_dimension, irreducible_polynomial, polynomial_terms):
        print(f"APN {polynomial_terms} is a duplicate and will not be stored.")
        return

    compute_all_invariants(apn_object)

    if not apn_object.invariants.get("is_apn", False):
        print("The function is not APN (differential uniformity != 2) and will not be stored.")
        return

    # Convert numeric invariants to the correct type.
    delta_rank_value = apn_object.invariants.get("delta_rank", None)
    if delta_rank_value is not None:
        delta_rank_value = int(delta_rank_value)

    gamma_rank_value = apn_object.invariants.get("gamma_rank", None)
    if gamma_rank_value is not None:
        gamma_rank_value = int(gamma_rank_value)

    algebraic_deg_value = apn_object.invariants.get("algebraic_degree", None)
    if algebraic_deg_value is not None:
        algebraic_deg_value = int(algebraic_deg_value)

    # Boolean columns.
    is_quad_value = bool(apn_object.invariants.get("is_quadratic", False))
    is_apn_value  = bool(apn_object.invariants.get("is_apn", False))
    is_mono_value = bool(apn_object.invariants.get("is_monomial", False))

    # Convert ODDS and ODWS if they're dictionaries to store as JSON.
    odds_value = apn_object.invariants.get("odds", "non-quadratic")
    if isinstance(odds_value, dict):
        odds_value = json.dumps(odds_value)

    odws_value = apn_object.invariants.get("odws", "non-quadratic")
    if isinstance(odws_value, dict):
        odws_value = json.dumps(odws_value)

    kto1_value = apn_object.invariants.get("k_to_1", "unknown")
    citation_value = apn_object.invariants.get("citation", citation_message)

    row_dict = {
        "field_n": int(field_dimension),
        "poly": json.dumps(polynomial_terms),
        "irr_poly": irreducible_polynomial,

        "odds": odds_value,
        "odws": odws_value,
        "delta_rank": delta_rank_value,
        "gamma_rank": gamma_rank_value,
        "algebraic_degree": algebraic_deg_value,
        "is_quadratic": is_quad_value,
        "is_apn": is_apn_value,
        "is_monomial": is_mono_value,
        "k_to_1": str(kto1_value),
        "citation": str(citation_value)
    }

    # Append & save.
    new_dataframe = pd.DataFrame([row_dict])
    combined_dataframe = pd.concat([existing_dataframe, new_dataframe], ignore_index=True)
    save_apn_dataframe_for_field(field_dimension, combined_dataframe)
    print(f"APN {polynomial_terms} saved => done.")


# --------------------------------------------------------------
# LOADING + RECONSTRUCTING APN OBJECTS
# --------------------------------------------------------------

def load_apn_objects_for_field_pandas(field_dimension: int) -> List[APN]:
    """
    Loads all APN entries for field dimension n from the Parquet file, reconstructs APN objects, 
    and populates their invariants with ODDS/ODWS, ranks and other invariants.
    """
    loaded_dataframe = load_apn_dataframe_for_field(field_dimension)
    if loaded_dataframe.empty:
        print(f"No APNs found in database for field_n={field_dimension}.")
        return []

    apn_list: List[APN] = []

    for index, row in loaded_dataframe.iterrows():
        try:
            # Parse polynomial from the stored JSON.
            polynomial_json_string = row.get("poly", "")
            polynomial_data = []
            if polynomial_json_string:
                try:
                    polynomial_data = json.loads(polynomial_json_string)
                except:
                    polynomial_data = []

            field_n_value  = int(row.get("field_n", field_dimension))
            irr_poly_value = row.get("irr_poly", "")

            # Build an APN object directly.
            apn_object = APN(polynomial_data, field_n_value, irr_poly_value)
            if not hasattr(apn_object, "invariants"):
                apn_object.invariants = {}

            # Reconstruct ODDS if it's JSON.
            odds_column_value = row.get("odds", "non-quadratic")
            if isinstance(odds_column_value, str):
                if odds_column_value == "non-quadratic":
                    apn_object.invariants["odds"] = "non-quadratic"
                else:
                    try:
                        parsed_odds = json.loads(odds_column_value)
                        if isinstance(parsed_odds, dict):
                            odds_dictionary = {}
                            for key, val in parsed_odds.items():
                                odds_dictionary[int(key)] = int(val)
                            apn_object.invariants["odds"] = odds_dictionary
                        else:
                            apn_object.invariants["odds"] = parsed_odds
                    except:
                        apn_object.invariants["odds"] = "non-quadratic"
            else:
                apn_object.invariants["odds"] = odds_column_value

            # Reconstruct ODWS if it's JSON.
            odws_column_value = row.get("odws", "non-quadratic")
            if isinstance(odws_column_value, str):
                if odws_column_value == "non-quadratic":
                    apn_object.invariants["odws"] = "non-quadratic"
                else:
                    try:
                        parsed_odws = json.loads(odws_column_value)
                        if isinstance(parsed_odws, dict):
                            odws_dictionary = {}
                            for key, val in parsed_odws.items():
                                odws_dictionary[int(key)] = int(val)
                            apn_object.invariants["odws"] = odws_dictionary
                        else:
                            apn_object.invariants["odws"] = parsed_odws
                    except:
                        apn_object.invariants["odws"] = "non-quadratic"
            else:
                apn_object.invariants["odws"] = odws_column_value

            # Numeric columns.
            delta_rank_value = row.get("delta_rank", None)
            if pd.notna(delta_rank_value):
                apn_object.invariants["delta_rank"] = int(delta_rank_value)

            gamma_rank_value = row.get("gamma_rank", None)
            if pd.notna(gamma_rank_value):
                apn_object.invariants["gamma_rank"] = int(gamma_rank_value)

            algebraic_degree_value = row.get("algebraic_degree", None)
            if pd.notna(algebraic_degree_value):
                apn_object.invariants["algebraic_degree"] = int(algebraic_degree_value)

            # Boolean columns.
            apn_object.invariants["is_quadratic"] = bool(row.get("is_quadratic", False))
            apn_object.invariants["is_apn"]       = bool(row.get("is_apn", False))
            apn_object.invariants["is_monomial"]  = bool(row.get("is_monomial", False))

            # k_to_1 column.
            apn_object.invariants["k_to_1"] = row.get("k_to_1","unknown")

            # Citation
            citation_value = row.get("citation","")
            apn_object.invariants["citation"] = citation_value if pd.notna(citation_value) else ""

            apn_list.append(apn_object)

        except Exception as reconstruct_error:
            print(f"Error building APN from row {index}: {reconstruct_error}")

    return apn_list