import click
from apn_storage_pandas import (
    load_match_list,
    save_match_list,
    load_apn_objects_for_field_pandas
)
from storage.input_json_storage import load_input_apns
from user_input_parser import PolynomialParser

@click.command("compare")
@click.option("--compare-type", type=click.Choice(["odds", "odws", "delta", "gamma", "all"]), default="all")
@click.option("--field-n", required=True, type=int)
@click.option("--debug", is_flag=True)
def compare_apns_cli(compare_type, field_n, debug):
    # Compares invariants of APNs in input_apns.json with the invariants of stored DB APNs for GF(2^n).
    # Invariant matches are stored in match_list.json.
    apn_list = load_input_apns()
    match_list_data = load_match_list()
    if not apn_list:
        click.echo("No APNs in the input list. Please run 'add-input' first.")
        return

    db_apns = load_apn_objects_for_field_pandas(field_n)
    if not db_apns:
        click.echo(f"No APNs found in the database for GF(2^{field_n}).")
        return

    if debug:
        click.echo(f"\nDebug Mode: Listing {len(db_apns)} DB APNs for GF(2^{field_n}):")
        for idx, db_apn in enumerate(db_apns):
            click.echo(f"\nDB_APN {idx}:\n{db_apn}")
        click.echo("\nEnd of DB APNs.\n")

    for input_idx, in_apn in enumerate(apn_list):
        if input_idx not in match_list_data:
            match_list_data[input_idx] = []

        existing_matches_map = {}
        for (m_apn, comp_types) in match_list_data[input_idx]:
            m_key = (
                m_apn.field_n,
                m_apn.irr_poly,
                tuple(tuple(term) for term in m_apn.representation.univariate_polynomial)
            )
            existing_matches_map[m_key] = (m_apn, comp_types)

        # Gather current invariants.
        in_odds = in_apn.invariants.get("odds", "non-quadratic")
        in_odws = in_apn.invariants.get("odws", "non-quadratic")
        in_gamma = in_apn.invariants.get("gamma_rank", None)
        in_delta = in_apn.invariants.get("delta_rank", None)

        # And one property needed for ODDS/ODWS comparison.
        in_is_quad = in_apn.properties.get("is_quadratic", False)

        # Restrict relevant types if non-quadratic.
        if not in_is_quad and compare_type in ["odds", "odws", "all"]:
            click.echo(f"For INPUT_APN {input_idx}, it is non-quadratic. Only gamma/delta can be compared.")
            if compare_type == "all":
                relevant_types = ["gamma", "delta"]
            elif compare_type in ["odds", "odws"]:
                relevant_types = []
            else:
                relevant_types = [compare_type]
        else:
            if compare_type == "all":
                relevant_types = ["odds", "odws", "gamma", "delta"]
            else:
                relevant_types = [compare_type]

        for db_index, db_apn in enumerate(db_apns):
            is_match = True
            db_odds = db_apn.invariants.get("odds", "non-quadratic")
            db_odws = db_apn.invariants.get("odws", "non-quadratic")
            db_gamma = db_apn.invariants.get("gamma_rank", None)
            db_delta = db_apn.invariants.get("delta_rank", None)

            for comp in relevant_types:
                if comp == "odds":
                    if in_odds != db_odds:
                        is_match = False
                        break
                elif comp == "odws":
                    if in_odws != db_odws:
                        is_match = False
                        break
                elif comp == "gamma":
                    if in_gamma != db_gamma:
                        is_match = False
                        break
                elif comp == "delta":
                    if in_delta != db_delta:
                        is_match = False
                        break

            if is_match:
                db_key = (
                    db_apn.field_n,
                    db_apn.irr_poly,
                    tuple(tuple(term) for term in db_apn.representation.univariate_polynomial)
                )
                if db_key in existing_matches_map:
                    (stored_apn, stored_comp_types) = existing_matches_map[db_key]
                    stored_comp_types.add(compare_type)
                else:
                    new_set = set([compare_type])
                    existing_matches_map[db_key] = (db_apn, new_set)

        new_matches_list = list(existing_matches_map.values())
        match_list_data[input_idx] = new_matches_list

        click.echo(f"For INPUT_APN {input_idx}, after comparing by '{compare_type}', "
                   f"found {len(match_list_data[input_idx])} matching APNs so far.")

    # And finally, save the match_list.json.
    save_match_list(match_list_data)