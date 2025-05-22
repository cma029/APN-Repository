import os
import pandas as pd
import json
from typing import List, Tuple
from vbf_object import VBF
from invariants import compute_all_invariants

def get_parquet_filename(dimension: int, is_apn: bool) -> str:
    """
    Returns the filename for storing VBFs of dimension n.
    If is_apn = True:  returns /database/apn/apn_data_{dimension}.parquet
    If is_apn = False: returns /database/vbf/vbf_data_{dimension}.parquet
    """
    subfolder = "apn" if is_apn else "vbf"
    file_prefix = "apn_data" if is_apn else "vbf_data"
    return os.path.join("database", subfolder, f"{file_prefix}_{dimension}.parquet")


def is_duplicate_candidate(dataframe: pd.DataFrame, dimension_n: int,
    irreducible_poly: str, polynomial_terms: List[Tuple[int,int]]) -> bool:
    # Check if (field_n, irr_poly, sorted poly) is already in the dataframe.
    sorted_candidate = sorted(polynomial_terms, key=lambda term: (term[0], term[1]))
    matching_rows = dataframe[
        (dataframe["field_n"] == dimension_n) &
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

def load_dataframe_for_dimension(dimension: int, is_apn: bool) -> pd.DataFrame:
    """
    Loads all VBFs for field degree n from the Parquet file, checking whether is_apn is True or False.
    If no file exists, returns an empty DataFrame with required columns.
    """
    filename = get_parquet_filename(dimension, is_apn)
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


def save_dataframe_for_dimension(dimension: int, dataframe: pd.DataFrame, is_apn: bool) -> None:
    # Writes dataframe to with Snappy compression.
    filename = get_parquet_filename(dimension, is_apn)
    # Ensure directories exist.
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    try:
        dataframe.to_parquet(filename, index=False, compression='snappy')
        print(f"Data successfully written to {filename} with Snappy compression.")
    except Exception as write_error:
        print(f"Error writing to {filename}: {write_error}")


# --------------------------------------------------------------
# STORING A NEW VBF FUNCTION
# --------------------------------------------------------------

def store_vbf_pandas(polynomial_terms: List[Tuple[int, int]], dimension: int, irreducible_polynomial: str,
    citation_message: str = "No citation provided.") -> None:
    """
    Build a VBF object from polynomial terms, compute invariants, and store the object as 
    a new row in the Parquet database for the specified dimension based on 'is_apn' == True.
    """
    try:
        vbf_object = VBF(polynomial_terms, dimension, irreducible_polynomial)
    except Exception as parse_err:
        print(f"Error constructing VBF from polynomial {polynomial_terms} => {parse_err}")
        return

    # Compute all invariants.
    compute_all_invariants(vbf_object)

    # Convert numeric invariants to the correct type.
    delta_rank_value = vbf_object.invariants.get("delta_rank", None)
    if delta_rank_value is not None:
        delta_rank_value = int(delta_rank_value)

    gamma_rank_value = vbf_object.invariants.get("gamma_rank", None)
    if gamma_rank_value is not None:
        gamma_rank_value = int(gamma_rank_value)

    algebraic_deg_value = vbf_object.invariants.get("algebraic_degree", None)
    if algebraic_deg_value is not None:
        algebraic_deg_value = int(algebraic_deg_value)

    # Boolean columns.
    is_quad_value = bool(vbf_object.invariants.get("is_quadratic", False))
    is_apn_value  = bool(vbf_object.invariants.get("is_apn", False))
    is_mono_value = bool(vbf_object.invariants.get("is_monomial", False))

    # Convert ODDS and ODWS if they're dictionaries to store as JSON.
    odds_value = vbf_object.invariants.get("odds", "non-quadratic")
    if isinstance(odds_value, dict):
        odds_value = json.dumps(odds_value)

    odws_value = vbf_object.invariants.get("odws", "non-quadratic")
    if isinstance(odws_value, dict):
        odws_value = json.dumps(odws_value)

    kto1_value = vbf_object.invariants.get("k_to_1", "unknown")
    citation_value = vbf_object.invariants.get("citation", citation_message)

    # Build the new row for storing.
    row_dict = {
        "field_n": int(dimension),
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

    # Load dataframe based on is_apn or not.
    existing_dataframe = load_dataframe_for_dimension(dimension, is_apn=is_apn_value)

    # Check for duplicates.
    poly_str = row_dict["poly"]
    poly_data = []
    if poly_str:
        try:
            poly_data = json.loads(poly_str)
        except:
            pass

    if is_duplicate_candidate(existing_dataframe, dimension, irreducible_polynomial, poly_data):
        print(f"VBF {polynomial_terms} is a duplicate and will not be stored.")
        return

    # Append & save.
    new_dataframe = pd.DataFrame([row_dict])
    combined_dataframe = pd.concat([existing_dataframe, new_dataframe], ignore_index=True)
    final_dataframe = combined_dataframe.drop_duplicates()
    save_dataframe_for_dimension(dimension, final_dataframe, is_apn=is_apn_value)

    if is_apn_value:
        print(f"APN {polynomial_terms} saved => /database/apn/apn_data_{dimension}.parquet")
    else:
        print(f"VBF {polynomial_terms} saved => /database/vbf/vbf_data_{dimension}.parquet")


# --------------------------------------------------------------
# LOADING + RECONSTRUCTING VBF OBJECTS
# --------------------------------------------------------------

def load_objects_for_dimension_pandas(dimension: int, is_apn: bool = True) -> List[VBF]:
    """
    Loads all entries for dimension n from the Parquet file, reconstructs VBF objects, and 
    populates their invariants.

    If is_apn=True (the default), loads APN entries from /database/apn/apn_data_{dimension}.parquet;
    if is_apn=False, loads from /database/vbf/vbf_data_{dimension}.parquet.
    """
    loaded_dataframe = load_dataframe_for_dimension(dimension, is_apn=is_apn)
    if loaded_dataframe.empty:
        print(
            f"No VBFs found for dimension n={dimension} in {'apn' if is_apn else 'vbf'} database."
        )
        return []

    vbf_list: List[VBF] = []

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

            dimension_n  = int(row.get("field_n", dimension))
            irr_poly_value = row.get("irr_poly", "")

            # Build an VBF object directly.
            vbf_object = VBF(polynomial_data, dimension_n, irr_poly_value)
            if not hasattr(vbf_object, "invariants"):
                vbf_object.invariants = {}

            # Reconstruct ODDS if it's JSON.
            odds_column_value = row.get("odds", "non-quadratic")
            if isinstance(odds_column_value, str):
                if odds_column_value == "non-quadratic":
                    vbf_object.invariants["odds"] = "non-quadratic"
                else:
                    try:
                        parsed_odds = json.loads(odds_column_value)
                        if isinstance(parsed_odds, dict):
                            odds_dictionary = {}
                            for key, val in parsed_odds.items():
                                odds_dictionary[int(key)] = int(val)
                            vbf_object.invariants["odds"] = odds_dictionary
                        else:
                            vbf_object.invariants["odds"] = parsed_odds
                    except:
                        vbf_object.invariants["odds"] = "non-quadratic"
            else:
                vbf_object.invariants["odds"] = odds_column_value

            # Reconstruct ODWS if it's JSON.
            odws_column_value = row.get("odws", "non-quadratic")
            if isinstance(odws_column_value, str):
                if odws_column_value == "non-quadratic":
                    vbf_object.invariants["odws"] = "non-quadratic"
                else:
                    try:
                        parsed_odws = json.loads(odws_column_value)
                        if isinstance(parsed_odws, dict):
                            odws_dictionary = {}
                            for key, val in parsed_odws.items():
                                odws_dictionary[int(key)] = int(val)
                            vbf_object.invariants["odws"] = odws_dictionary
                        else:
                            vbf_object.invariants["odws"] = parsed_odws
                    except:
                        vbf_object.invariants["odws"] = "non-quadratic"
            else:
                vbf_object.invariants["odws"] = odws_column_value

            # Numeric columns.
            delta_rank_value = row.get("delta_rank", None)
            if pd.notna(delta_rank_value):
                vbf_object.invariants["delta_rank"] = int(delta_rank_value)

            gamma_rank_value = row.get("gamma_rank", None)
            if pd.notna(gamma_rank_value):
                vbf_object.invariants["gamma_rank"] = int(gamma_rank_value)

            algebraic_degree_value = row.get("algebraic_degree", None)
            if pd.notna(algebraic_degree_value):
                vbf_object.invariants["algebraic_degree"] = int(algebraic_degree_value)

            # Boolean columns.
            vbf_object.invariants["is_quadratic"] = bool(row.get("is_quadratic", False))
            vbf_object.invariants["is_apn"]       = bool(row.get("is_apn", False))
            vbf_object.invariants["is_monomial"]  = bool(row.get("is_monomial", False))

            # k_to_1 column.
            vbf_object.invariants["k_to_1"] = row.get("k_to_1","unknown")

            # Citation
            citation_value = row.get("citation","")
            vbf_object.invariants["citation"] = citation_value if pd.notna(citation_value) else ""

            vbf_list.append(vbf_object)

        except Exception as reconstruct_error:
            print(f"Error building VBF from row {index}: {reconstruct_error}")

    return vbf_list