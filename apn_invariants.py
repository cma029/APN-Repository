import re
import galois
from collections import OrderedDict, Counter
from typing import List, Tuple, Optional, Dict, Sequence
from computations.rank.delta_rank import DeltaRankComputation
from computations.rank.gamma_rank import GammaRankComputation
from computations.spectra.od_differential_spectrum import ODDifferentialSpectrumComputation
from computations.spectra.od_walsh_spectrum import ODWalshSpectrumComputation
from c_invariants_bindings import (
    create_function_from_truth_table,
    create_function_from_truth_table_and_poly,
    destroy_function,
    function_is_apn,
    function_differential_uniformity,
    function_k_to_1,
    function_algebraic_degree,
    function_is_monomial,
    function_is_quadratic
)

def parse_irreducible_poly_str(poly_str):
    # Converts a polynomial string (e.g. 'x^6 + x^4 + x^3 + x + 1') into an integer bitmask.
    # Bit for x^k is set if k is in the polynomial. Example: 'x^6 + x^4 + x^3 + x + 1' -> 0b01011011 (0x5B).

    # Clean up spaces.
    s = poly_str.replace(" ", "").replace("^+", "^")

    # Manual parse with a pattern for x^(\d+) or x or 1.
    terms = s.split('+')
    bitmask = 0
    for t in terms:
        if t == '1':
            bitmask |= (1 << 0)
        elif t == 'x':
            bitmask |= (1 << 1)
        else:
            # Might be x^k.
            if t.startswith('x^'):
                k_str = t[2:]
                k = int(k_str)
                bitmask |= (1 << k)
    return bitmask


def _create_func_ptr_from_apn(apn):
    # Internal helper that return a function pointer (ptr) handle in C++.
    tt = apn._get_truth_table_list()
    poly_str = apn.irr_poly.strip()
    if len(poly_str) == 0:
        # No polynomial => skip.
        return create_function_from_truth_table(tt)

    poly_bits = parse_irreducible_poly_str(poly_str)
    return create_function_from_truth_table_and_poly(tt, poly_bits)


def compute_is_apn(apn):
    if "is_apn" in apn.invariants:
        return

    func_ptr = _create_func_ptr_from_apn(apn)
    try:
        is_apn = function_is_apn(func_ptr)
        # For the Differential Uniformity.
        # du = function_differential_uniformity(func_ptr)
    finally:
        destroy_function(func_ptr)

    apn.invariants['is_apn'] = bool(is_apn)
    # apn.invariants['differential_uniformity'] = du

def compute_anf_invariants(apn):
    # It’s cheaper to compute algebraic_degree, is_monomial, and is_quadratic
    # in one pass since they all use the same _create_func_ptr_from_apn().
    # When computing the Algebraic Normal Form (ANF), do all three:
    """
      - apn.invariants['algebraic_degree']
      - apn.invariants['is_monomial']
      - apn.invariants['is_quadratic']
    """
    if all(key in apn.invariants for key in ["algebraic_degree", "is_monomial", "is_quadratic"]):
        return

    func_ptr = _create_func_ptr_from_apn(apn)
    try:
        deg = function_algebraic_degree(func_ptr)
        monomial_flag = function_is_monomial(func_ptr)
        quad_flag = function_is_quadratic(func_ptr)
    finally:
        destroy_function(func_ptr)

    apn.invariants['algebraic_degree'] = deg
    apn.invariants['is_monomial'] = bool(monomial_flag)
    apn.invariants['is_quadratic'] = bool(quad_flag)


def compute_k_to_1(apn):
    if "k_to_1" in apn.invariants:
        return

    func_ptr = _create_func_ptr_from_apn(apn)
    try:
        k = function_k_to_1(func_ptr)
    finally:
        destroy_function(func_ptr)

    if k == -1:
        apn.invariants['k_to_1'] = 'not uniform'
    else:
        apn.invariants['k_to_1'] = f'{k}-to-1'


def compute_delta_rank(apn):
    if "delta_rank" in apn.invariants:
        return

    try:
        apn_tt = apn.get_truth_table()
        delta_comp = DeltaRankComputation()
        val = delta_comp.compute_rank(apn_tt)
        apn.invariants["delta_rank"] = val
    except:
        apn.invariants["delta_rank"] = None


def compute_gamma_rank(apn):
    if "gamma_rank" in apn.invariants:
        return

    try:
        apn_tt = apn.get_truth_table()
        gamma_comp = GammaRankComputation()
        val = gamma_comp.compute_rank(apn_tt)
        apn.invariants["gamma_rank"] = val
    except:
        apn.invariants["gamma_rank"] = None


def compute_odds(apn):
    if "odds" in apn.invariants:
        return

    if "is_quadratic" not in apn.invariants:
        compute_anf_invariants(apn)

    if not apn.invariants.get("is_quadratic", False):
        apn.invariants.setdefault("odds", "non-quadratic")
        return

    try:
        apn_tt = apn.get_truth_table()
        odd_comp = ODDifferentialSpectrumComputation()
        res = odd_comp.compute_spectrum(apn_tt)
        apn.invariants["odds"] = {int(k): int(v) for k,v in res.items()}
    except:
        apn.invariants["odds"] = "non-quadratic"


def compute_odws(apn):
    if "odws" in apn.invariants:
        return

    if "is_quadratic" not in apn.invariants:
        compute_anf_invariants(apn)

    if not apn.invariants.get("is_quadratic", False):
        apn.invariants.setdefault("odws", "non-quadratic")
        return

    try:
        apn_tt = apn.get_truth_table()
        odw_comp = ODWalshSpectrumComputation()
        res = odw_comp.compute_spectrum(apn_tt)
        apn.invariants["odws"] = {int(k): int(v) for k,v in res.items()}
    except:
        apn.invariants["odws"] = "non-quadratic"


def compute_all_invariants(apn):

    compute_anf_invariants(apn)

    compute_k_to_1(apn)

    # Rank:
    compute_delta_rank(apn)
    compute_gamma_rank(apn)

    # Ortho-Derivative spectra:
    compute_odds(apn)
    compute_odws(apn)

    reorder_invariants(apn)


def reorder_invariants(apn):
    desired_order = [
        "odds",
        "odws",
        "delta_rank",
        "gamma_rank",
        "is_apn",
        "algebraic_degree",
        "is_quadratic",
        "is_monomial",
        "k_to_1",
        "differential_uniformity",
    ]
    old_map = apn.invariants
    new_map = OrderedDict()

    for key in desired_order:
        if key in old_map:
            new_map[key] = old_map[key]

    # Append leftover keys at the end.
    for k in old_map:
        if k not in new_map:
            new_map[k] = old_map[k]

    apn.invariants = dict(new_map)