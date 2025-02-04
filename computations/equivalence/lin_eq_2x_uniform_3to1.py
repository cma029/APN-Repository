# lin_eq_2x_uniform_3to1.py
# Description: linear equivalence test for testing two uniform 3-to-1 APNs.

import os
import sys
import ctypes
from ctypes import c_size_t, c_ulong, c_bool, POINTER, byref
from typing import List
from computations.equivalence.base_equivalence import EquivalenceTest

# Determine the library name based on platform
if sys.platform.startswith("win"):
    lib_name = "check_lin_eq_2x_uniform_3to1.dll"
elif sys.platform.startswith("darwin"):
    lib_name = "libcheck_lin_eq_2x_uniform_3to1.dylib"
else:
    lib_name = "libcheck_lin_eq_2x_uniform_3to1.so"

# Build the full path to the native library
this_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(this_dir, "..", "..", "c_src", lib_name)
lib_path = os.path.abspath(lib_path)

# Load the library via ctypes
clib = ctypes.CDLL(lib_path)

# Define the C structure matching the snippet
class VbfTt(ctypes.Structure):
    _fields_ = [
        ("vbf_tt_dimension", c_size_t),
        ("vbf_tt_number_of_entries", c_size_t),
        ("vbf_tt_values", POINTER(c_ulong)),
    ]

# is_canonical_triplicate_c
clib.check_is_canonical_triplicate.argtypes = [ctypes.POINTER(VbfTt)]
clib.check_is_canonical_triplicate.restype  = c_bool

# check_lin_eq_2x_uniform_3to1
clib.run_alg1_equivalence_test.argtypes = [ctypes.POINTER(VbfTt), ctypes.POINTER(VbfTt)]
clib.run_alg1_equivalence_test.restype  = c_bool

# --------------------------------------------------------------
# Internal helper to create the C structure from a Python list
# --------------------------------------------------------------
def _create_vbf_tt(tt_values: List[int], dimension: int):
    num_entries = 1 << dimension
    if len(tt_values) != num_entries:
        raise ValueError(f"TT length {len(tt_values)} != 2^{dimension}")

    ArrayType = c_ulong * num_entries
    backing_array = ArrayType(*tt_values)

    vbf_struct = VbfTt()
    vbf_struct.vbf_tt_dimension = dimension
    vbf_struct.vbf_tt_number_of_entries = num_entries
    vbf_struct.vbf_tt_values = ctypes.cast(backing_array, POINTER(c_ulong))
    return vbf_struct, backing_array

def is_canonical_triplicate_python(tt_values: List[int], dimension: int) -> bool:
    # Returns True iff the function with LUT=tt_values is canonical 3-to-1.
    vbf, arr = _create_vbf_tt(tt_values, dimension)
    result = clib.check_is_canonical_triplicate(byref(vbf))
    return bool(result)

def check_lin_eq_2x_uniform_3to1_python(F_tt: List[int], F_dim: int, G_tt: List[int], G_dim: int) -> bool:
    # Returns True iff F and G are linearly equivalent canonical 3-to-1.
    vbfF, arrF = _create_vbf_tt(F_tt, F_dim)
    vbfG, arrG = _create_vbf_tt(G_tt, G_dim)
    result = clib.run_alg1_equivalence_test(byref(vbfF), byref(vbfG))
    return bool(result)

def check_2x_uniform_3to1_equivalence_python(ttF, nF, ttG, nG):
    return check_lin_eq_2x_uniform_3to1_python(ttF, nF, ttG, nG)

class Uniform3to1EquivalenceTest(EquivalenceTest):
    """
    Linear equivalence test for testing two uniform 3-to-1 APNs.
    """

    def are_equivalent(self, apnF, apnG):
        if apnF.field_n != apnG.field_n:
            pass
        f_tt = apnF._get_truth_table_list()
        g_tt = apnG._get_truth_table_list()
        return check_2x_uniform_3to1_equivalence_python(f_tt, apnF.field_n, g_tt, apnG.field_n)