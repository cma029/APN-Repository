import galois
from representations.truth_table_representation import TruthTableRepresentation
from computations.rank.delta_rank import DeltaRankComputation
from computations.rank.gamma_rank import GammaRankComputation
from computations.spectra.od_differential_spectrum import ODDifferentialSpectrumComputation
from computations.spectra.od_walsh_spectrum import ODWalshSpectrumComputation
from c_invariants_bindings import (
    create_function_from_truth_table,
    create_function_from_truth_table_and_poly,
    destroy_function,
    function_differential_uniformity,
    function_k_to_1,
    function_algebraic_degree,
    function_is_monomial,
    function_is_quadratic
)

def parse_irreducible_poly_str(poly_str: str) -> int:
    # Converts a polynomial string (e.g. 'x^6 + x^4 + x^3 + x + 1') into an integer bitmask.
    # Bit for x^k is set if k is in the polynomial. Example: 'x^6 + x^4 + x^3 + x + 1' -> 0b01011011 (0x5B).
    cleaned_str = poly_str.replace(" ", "").replace("^+", "^")
    terms = cleaned_str.split('+')
    bitmask = 0
    for t in terms:
        if t == '1':
            bitmask |= (1 << 0)
        elif t == 'x':
            bitmask |= (1 << 1)
        else:
            # Might be x^k.
            if t.startswith('x^'):
                k_exponent = int(t[2:])
                bitmask |= (1 << k_exponent)
    return bitmask


def _create_func_ptr_from_apn(apn):
    # Internal helper that return a function pointer (ptr) handle in C++.
    apn_tt = apn._get_truth_table_list()
    if not apn.irr_poly.strip():
        # No polynomial => skip.
        return create_function_from_truth_table(apn_tt)
    
    poly_bits = parse_irreducible_poly_str(apn.irr_poly.strip())
    return create_function_from_truth_table_and_poly(apn_tt, poly_bits)


def compute_is_apn(apn):
    if "is_apn" in apn.invariants:
        return

    func_ptr = _create_func_ptr_from_apn(apn)
    try:
        diff_uni = function_differential_uniformity(func_ptr)
    finally:
        destroy_function(func_ptr)

    if diff_uni == 2:
        apn.invariants["is_apn"] = True
    else:
        apn.invariants["is_apn"] = False
        print(f"Warning: Differential Uniformity = {diff_uni}")


def compute_anf_invariants(apn):
    # It’s cheaper to compute algebraic_degree, is_monomial, and is_quadratic
    # in one pass since they all use the same _create_func_ptr_from_apn().
    # When computing the Algebraic Normal Form (ANF), do all three:
    if all(key in apn.invariants for key in ["algebraic_degree", "is_monomial", "is_quadratic"]):
        return

    func_ptr = _create_func_ptr_from_apn(apn)
    try:
        degree = function_algebraic_degree(func_ptr)
        monomial_flag = function_is_monomial(func_ptr)
        quadratic_flag = function_is_quadratic(func_ptr)
    finally:
        destroy_function(func_ptr)

    apn.invariants["algebraic_degree"] = degree
    apn.invariants["is_monomial"] = bool(monomial_flag)
    apn.invariants["is_quadratic"] = bool(quadratic_flag)

def compute_k_to_1(apn):
    if "k_to_1" in apn.invariants:
        return

    func_ptr = _create_func_ptr_from_apn(apn)
    try:
        k_value = function_k_to_1(func_ptr)
    finally:
        destroy_function(func_ptr)
    if k_value == -1:
        apn.invariants["k_to_1"] = "not uniform"
    else:
        apn.invariants["k_to_1"] = f"{k_value}-to-1"


def compute_delta_rank(apn):
    if "delta_rank" in apn.invariants:
        return

    try:
        apn_tt = apn._get_truth_table_list()
        temporary_apn = apn.__class__.from_representation(
            TruthTableRepresentation(apn_tt),
            apn.field_n,
            apn.irr_poly
        )
        delta_comp = DeltaRankComputation()
        rank_val = delta_comp.compute_rank(temporary_apn)
        apn.invariants["delta_rank"] = rank_val
    except:
        apn.invariants["delta_rank"] = None


def compute_gamma_rank(apn):
    if "gamma_rank" in apn.invariants:
        return

    try:
        apn_tt = apn._get_truth_table_list()
        temporary_apn = apn.__class__.from_representation(
            TruthTableRepresentation(apn_tt),
            apn.field_n,
            apn.irr_poly
        )
        gamma_comp = GammaRankComputation()
        rank_val = gamma_comp.compute_rank(temporary_apn)
        apn.invariants["gamma_rank"] = rank_val
    except:
        apn.invariants["gamma_rank"] = None


def compute_odds(apn):
    if "odds" in apn.invariants:
        return

    if "is_quadratic" not in apn.invariants:
        compute_anf_invariants(apn)

    if not apn.invariants.get("is_quadratic", False):
        apn.invariants["odds"] = "non-quadratic"
        return

    try:
        apn_tt = apn._get_truth_table_list()
        temporary_apn = apn.__class__.from_representation(
            TruthTableRepresentation(apn_tt),
            apn.field_n,
            apn.irr_poly
        )
        odd_comp = ODDifferentialSpectrumComputation()
        spectrum_res = odd_comp.compute_spectrum(temporary_apn)
        apn.invariants["odds"] = {int(key): int(val) for key, val in spectrum_res.items()}
    except:
        apn.invariants["odds"] = "non-quadratic"


def compute_odws(apn):
    if "odws" in apn.invariants:
        return

    if "is_quadratic" not in apn.invariants:
        compute_anf_invariants(apn)

    if not apn.invariants.get("is_quadratic", False):
        apn.invariants["odws"] = "non-quadratic"
        return

    try:
        apn_tt = apn._get_truth_table_list()
        temporary_apn = apn.__class__.from_representation(
            TruthTableRepresentation(apn_tt),
            apn.field_n,
            apn.irr_poly
        )
        odw_comp = ODWalshSpectrumComputation()
        spectrum_res = odw_comp.compute_spectrum(temporary_apn)
        apn.invariants["odws"] = {int(key): int(val) for key, val in spectrum_res.items()}
    except:
        apn.invariants["odws"] = "non-quadratic"

def compute_all_invariants(apn):

    # Invariants:
    compute_anf_invariants(apn)
    compute_is_apn(apn)
    compute_k_to_1(apn)

    # Ortho-Derivative spectra:
    compute_odds(apn)
    compute_odws(apn)

    # Rank:
    compute_delta_rank(apn)
    compute_gamma_rank(apn)

    reorder_invariants(apn)

def reorder_invariants(apn):
    desired = [
        "odds",
        "odws",
        "delta_rank",
        "gamma_rank",
        "algebraic_degree",
        "is_quadratic",
        "is_apn",
        "is_monomial",
        "k_to_1"
    ]
    old_invariants = apn.invariants
    new_invariants = {}

    for key in desired:
        if key in old_invariants:
            new_invariants[key] = old_invariants[key]

    # Append leftover keys at the end.
    for leftover_key in old_invariants:
        if leftover_key not in new_invariants:
            new_invariants[leftover_key] = old_invariants[leftover_key]
    apn.invariants = new_invariants