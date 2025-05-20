from __future__ import annotations
import ctypes
import os
import sys
from registry import REG
from computations.equivalence.base_equivalence import EquivalenceTest


# ----------------------------------------------------------------------------
# Determine platform-specific C library name for the compiled code.
# ----------------------------------------------------------------------------
if sys.platform.startswith("win"):
    LIB_NAME = "check_lin_eq_2x_uniform_3to1.dll"
elif sys.platform.startswith("darwin"):
    LIB_NAME = "libcheck_lin_eq_2x_uniform_3to1.dylib"
else:
    LIB_NAME = "libcheck_lin_eq_2x_uniform_3to1.so"

LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "c_src", LIB_NAME))
CLIB = ctypes.CDLL(LIB_PATH)

c_ulong = ctypes.c_ulong


# ----------------------------------------------------------------------------
# Define vbf_tt structure in Python (matching check_lin_eq_2x_uniform_3to1.h).
# ----------------------------------------------------------------------------
class VbfTt(ctypes.Structure):
    _fields_ = [
        ("vbf_tt_dimension", ctypes.c_size_t),
        ("vbf_tt_number_of_entries", ctypes.c_size_t),
        ("vbf_tt_values", ctypes.POINTER(c_ulong)),
    ]


# ----------------------------------------------------------------------------
# Expose the relevant C functions for in-memory usage.
# ----------------------------------------------------------------------------

# Bool is_canonical_triplicate_c(vbf_tt *F);
CLIB.is_canonical_triplicate_c.argtypes = [ctypes.POINTER(VbfTt)]
CLIB.is_canonical_triplicate_c.restype = ctypes.c_bool

# Bool check_lin_eq_2x_uniform_3to1(vbf_tt *F, vbf_tt *G);
CLIB.check_lin_eq_2x_uniform_3to1.argtypes = [
    ctypes.POINTER(VbfTt), ctypes.POINTER(VbfTt)
]

CLIB.check_lin_eq_2x_uniform_3to1.restype = ctypes.c_bool


# ----------------------------------------------------------------------------
# Local helpers for building a VbfTt (vectorial Boolean function truth table).
# ----------------------------------------------------------------------------
def _build_vbftt(tt_values: list[int], dimension: int):
    arr_type = c_ulong * len(tt_values)
    c_array = arr_type(*tt_values)
    return VbfTt(dimension, len(tt_values), c_array), c_array # Keep c_array alive.


def _is_triplicate(tt_values: list[int], dimensio: int) -> bool:
    vbf, _ = _build_vbftt(tt_values, dimensio)
    return bool(CLIB.is_canonical_triplicate_c(ctypes.byref(vbf)))


def _linear_equivalence_3to1(F_values: list[int], G_values: list[int], dimension: int) -> bool:
    vbfF, arrF = _build_vbftt(F_values, dimension)
    vbfG, arrG = _build_vbftt(G_values, dimension)

    # The check_lin_eq_2x_uniform_3to1 function expects both to be canonical triplicates.
    return bool(CLIB.check_lin_eq_2x_uniform_3to1(ctypes.byref(vbfF), ctypes.byref(vbfG)))


# ----------------------------------------------------------------------------
# The Uniform3to1EquivalenceTest class (registered equivalence class).
# ----------------------------------------------------------------------------
@REG.register("equivalence", "uni3to1")
class Uniform3to1EquivalenceTest(EquivalenceTest):
    """
    Return True if both object_F and object_G are canonical triplicate (3-to-1),
    and are linearly equivalent. Return False otherwise.
    """
    name = "uni3to1"

    def are_equivalent(self, object_F, object_G) -> bool:
        if object_F.field_n != object_G.field_n:
            return ValueError("f and g have different sizes, cannot be CCZ tested.")

        dimension = object_F.field_n
        truth_table_F = object_F._get_truth_table_list()
        truth_table_G = object_G._get_truth_table_list()

        # Check if both are canonical triplicate (3-to-1).
        if not _is_triplicate(truth_table_F, dimension):
            return False
        if not _is_triplicate(truth_table_G, dimension):
            return False

        # If both are canonical triplicate, check for linear equivalence.
        return _linear_equivalence_3to1(truth_table_F, truth_table_G, dimension)