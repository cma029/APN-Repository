# apn_storage_pandas.py
# Description: Functions for storing and loading APN data using Pandas DataFrames.

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
from computations.rank.gamma_rank import GammaRankComputation
from computations.rank.delta_rank import DeltaRankComputation
from user_input_parser import PolynomialParser
from apn_object import APN
from apn_is_quadratic import is_quadratic_apn
from apn_properties import compute_apn_properties

def get_parquet_filename(n: int) -> str:
    # Returns the filename for storing APNs of field degree n. E.g., for n=6 -> 'apn_data_6.parquet'.
    return f"apn_data_{n}.parquet"

def poly_to_key(poly: List[Tuple[int, int]]) -> str:
    # Converts a polynomial list [(coeff_exp, mon_exp), ...] into a canonical JSON string for 
    # duplicate-checking by sorting the terms.
    poly_sorted = sorted(poly, key=lambda t: (t[0], t[1]))
    return json.dumps(poly_sorted)


# --------------------------------------------------------------
# READING AND WRITING FILES
# --------------------------------------------------------------

def load_apn_df_for_field(n: int) -> pd.DataFrame:
    # Loads all APNs for field degree n from the Parquet file.
    # If no file exists, returns an empty DataFrame with the specified columns.
    filename = get_parquet_filename(n)
    if not os.path.isfile(filename):
        # Define columns
        columns = [
            "field_n", "irr_poly", "poly_key", "poly",
            "odds_str", "odws_str", "gamma_rank", "delta_rank", "citation"
        ]
        return pd.DataFrame(columns=columns)
    try:
        return pd.read_parquet(filename)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        # Return empty DataFrame to avoid crashes
        columns = [
            "field_n", "irr_poly", "poly_key", "poly",
            "odds_str", "odws_str", "gamma_rank", "delta_rank", "citation"
        ]
        return pd.DataFrame(columns=columns)


def save_apn_df_for_field(n: int, df: pd.DataFrame) -> None:
    # Overwrites the Parquet file for field degree n with the given DataFrame.
    # param df: pandas DataFrame containing APN data
    filename = get_parquet_filename(n)
    try:
        df.to_parquet(filename, index=False, compression='snappy')
        print(f"Data successfully written to {filename} with Snappy compression.")
    except Exception as e:
        print(f"Error writing to {filename}: {e}")


# --------------------------------------------------------------
# STORING A NEW APN
# --------------------------------------------------------------

def store_apn_pandas(
    poly: List[Tuple[int, int]],
    field_n: int,
    irr_poly: str,
    citation: str = "No citation provided."
) -> None:

    # 1) Initialize PolynomialParser and parse the polynomial into an APN object
    parser = PolynomialParser()
    try:
        apn = parser.parse_univariate_polynomial(poly, field_n, irr_poly)
    except Exception as e:
        print(f"Error parsing polynomial {poly} for field_n={field_n}: {e}")
        return

    # Compute APN properties
    compute_apn_properties(apn)    
    
    # 2) Convert APN to truth table and compute differential uniformity
    try:
        apn_tt = apn.get_truth_table()
        tt = apn_tt.representation.truth_table
    except Exception as e:
        print(f"Error converting APN to truth table: {e}")
        return

    # 3) Check if the APN is valid (differential uniformity == 2)
    is_apn = (apn.properties.get("is_apn", False))
    if not is_apn:
        print(f"APN {poly} is not valid (differential_uniformity != 2); skipping storage.")
        return

    # 4) Determine if the APN is quadratic
    try:
        is_quadratic = apn.properties.get("is_quadratic", False)
    except Exception as e:
        print(f"Error determining if APN {poly} is quadratic: {e}")
        is_quadratic = False  # Default to non-quadratic if error occurs

    # 5) Compute Gamma and Delta ranks using multi-threading (and OD spectra if is_quadratic is True).
    g_rank = None
    d_rank = None
    odds_dict = {}
    odws_dict = {}

    num_workers = multiprocessing.cpu_count()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        from computations.rank.gamma_rank import GammaRankComputation
        from computations.rank.delta_rank import DeltaRankComputation
        gamma_comp = GammaRankComputation()
        delta_comp = DeltaRankComputation()

        future_gamma = executor.submit(gamma_comp.compute_rank, apn_tt)
        future_delta = executor.submit(delta_comp.compute_rank, apn_tt)

        # If APN is quadratic, also compute ODDS and ODWS
        if is_quadratic:
            from computations.spectra.od_differential_spectrum import ODDifferentialSpectrumComputation
            from computations.spectra.od_walsh_spectrum import ODWalshSpectrumComputation

            odd_comp = ODDifferentialSpectrumComputation()
            odw_comp = ODWalshSpectrumComputation()

            future_odds = executor.submit(odd_comp.compute_spectrum, apn_tt)
            future_odws = executor.submit(odw_comp.compute_spectrum, apn_tt)
        else:
            future_odds = None
            future_odws = None

        try:
            g_rank = future_gamma.result()
        except Exception as e:
            print(f"Error computing Gamma Rank for field_n={field_n}: {e}")
        try:
            d_rank = future_delta.result()
        except Exception as e:
            print(f"Error computing Delta Rank for field_n={field_n}: {e}")

        if is_quadratic and future_odds and future_odws:
            try:
                odds_dict = future_odds.result()
            except Exception as e:
                print(f"Error computing OD Differential Spectrum for field_n={field_n}: {e}")
                odds_dict = {}

            try:
                odws_dict = future_odws.result()
            except Exception as e:
                print(f"Error computing OD Extended Walsh Spectrum for field_n={field_n}: {e}")
                odws_dict = {}

    # Prepare the final strings for ODDS/ODWS
    if is_quadratic:
        import json
        odds_str = json.dumps(odds_dict)
        odws_str = json.dumps(odws_dict)
    else:
        odds_str = "Non-quadratic"
        odws_str = "Non-quadratic"
        print(f"APN {poly} is not quadratic; ODDS and ODWS are set to 'Non-quadratic'.")

    # 6) Build a unique key for duplicate checking
    poly_key_str = poly_to_key(poly)

    # 7) Create a dictionary for the new APN
    new_apn_dict = {
        "field_n": field_n,
        "irr_poly": irr_poly,
        "poly_key": poly_key_str,
        "poly": json.dumps(poly),
        "odds_str": odds_str,
        "odws_str": odws_str,
        "gamma_rank": g_rank,
        "delta_rank": d_rank,
        "citation": citation
    }

    # 8) Load existing DataFrame for the field
    df = load_apn_df_for_field(field_n)

    # 9) Check for duplicates
    is_duplicate = (
        (df["field_n"] == field_n) &
        (df["irr_poly"] == irr_poly) &
        (df["poly_key"] == poly_key_str)
    )
    if not df[is_duplicate].empty:
        print(f"APN {poly} already exists in apn_data_{field_n}.parquet; skipping addition.")
        return

    # 10) Append the new APN to the DataFrame using pd.concat
    new_df = pd.DataFrame([new_apn_dict])
    try:
        df = pd.concat([df, new_df], ignore_index=True)
    except Exception as e:
        print(f"Error appending new APN to DataFrame: {e}")
        return

    # 11) Save the updated DataFrame back to the Parquet file with Snappy compression
    save_apn_df_for_field(field_n, df)
    print(f"APN {poly} successfully added to apn_data_{field_n}.parquet.")


# --------------------------------------------------------------
# LOADING + RECONSTRUCTING APN OBJECTS
# --------------------------------------------------------------

def load_apn_objects_for_field_pandas(n: int) -> List[APN]:
    # Loads all APN entries for field degree n from the Parquet file, reconstructs APN objects, 
    # and populates their invariants with ODDS/ODWS data and ranks and more.
    df = load_apn_df_for_field(n)
    if df.empty:
        print(f"No APNs found for field_n={n}.")
        return []

    apn_list = []
    parser = PolynomialParser()

    import json

    for index, row in df.iterrows():
        try:
            poly = json.loads(row["poly"])

            # Reconstruct APN object
            apn = parser.parse_univariate_polynomial(poly, n, row["irr_poly"])

            # Populate invariants with stored data
            if row["odds_str"] == "Non-quadratic" or row["odws_str"] == "Non-quadratic":
                # Non-quadratic APN; set spectra to "non-quadratic"
                apn.invariants["odds"] = "non-quadratic"
                apn.invariants["odws"] = "non-quadratic"
            else:
                # Quadratic APN; load spectra from JSON strings
                apn.invariants["odds"] = json.loads(row["odds_str"]) if pd.notna(row["odds_str"]) else {}
                apn.invariants["odws"] = json.loads(row["odws_str"]) if pd.notna(row["odws_str"]) else {}
            
            # Load gamma_rank and delta_rank
            apn.invariants["gamma_rank"] = row["gamma_rank"] if pd.notna(row["gamma_rank"]) else None
            apn.invariants["delta_rank"] = row["delta_rank"] if pd.notna(row["delta_rank"]) else None
            apn.invariants["citation"] = row["citation"] if pd.notna(row["citation"]) else ""

            apn_list.append(apn)
        except Exception as e:
            print(f"Error reconstructing APN at index {index}: {e}")
            continue

    print(f"Loaded {len(apn_list)} APN objects for field_n={n}.")
    return apn_list