from registry import REG
from vbf_object import VBF
from computations.invariants.anf_invariants import anf_invariants
from computations.invariants.differential_uniformity import differential_uniformity

@REG.register("invariant", "is_apn")
def is_apn(vbf: VBF):
    if "is_apn" not in vbf.invariants:
        differential_uniformity(vbf)
    return vbf.invariants["is_apn"]

@REG.register("invariant", "algebraic_degree")
def algebraic_degree(vbf: VBF):
    if "algebraic_degree" in vbf.invariants:
        return vbf.invariants["algebraic_degree"]
    anf_invariants(vbf)
    return vbf.invariants["algebraic_degree"]

@REG.register("invariant", "is_monomial")
def is_monomial(vbf: VBF):
    if "is_monomial" in vbf.invariants:
        return vbf.invariants["is_monomial"]
    anf_invariants(vbf)
    return vbf.invariants["is_monomial"]

@REG.register("invariant", "is_quadratic")
def is_quadratic(vbf: VBF):
    if "is_quadratic" in vbf.invariants:
        return vbf.invariants["is_quadratic"]
    anf_invariants(vbf)
    return vbf.invariants["is_quadratic"]