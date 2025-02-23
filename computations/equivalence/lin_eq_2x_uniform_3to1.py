import ctypes
import os
import sys
from computations.equivalence.base_equivalence import EquivalenceTest


# ----------------------------------------------------------------------------
# Determine platform-specific library name for the compiled code.
# ----------------------------------------------------------------------------
if sys.platform.startswith("win"):
    LIB_NAME = "check_lin_eq_2x_uniform_3to1.dll"
elif sys.platform.startswith("darwin"):
    LIB_NAME = "libcheck_lin_eq_2x_uniform_3to1.dylib"
else:
    LIB_NAME = "libcheck_lin_eq_2x_uniform_3to1.so"


this_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(this_dir, "..", "..", "c_src", LIB_NAME)
lib_path = os.path.abspath(lib_path)

_check_lib = ctypes.CDLL(lib_path)


c_uint8 = ctypes.c_uint8
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
_check_lib.is_canonical_triplicate_c.argtypes = [ctypes.POINTER(VbfTt)]
_check_lib.is_canonical_triplicate_c.restype  = ctypes.c_bool

# Bool check_lin_eq_2x_uniform_3to1(vbf_tt *F, vbf_tt *G);
_check_lib.check_lin_eq_2x_uniform_3to1.argtypes = [ctypes.POINTER(VbfTt),
                                                    ctypes.POINTER(VbfTt)]
_check_lib.check_lin_eq_2x_uniform_3to1.restype  = ctypes.c_bool

# ----------------------------------------------------------------------------
# Helper for building a VbfTt from a Python list.
# ----------------------------------------------------------------------------
def _create_vbf_tt_from_list(tt_values, dimension):
    length = (1 << dimension)
    if len(tt_values) != length:
        raise ValueError(f"Expected {length} values, got {len(tt_values)}.")

    arr_type = c_ulong * length
    c_array = arr_type(*tt_values)

    vbf = VbfTt()
    vbf.vbf_tt_dimension = dimension
    vbf.vbf_tt_number_of_entries = length
    vbf.vbf_tt_values = ctypes.cast(c_array, ctypes.POINTER(c_ulong))

    return vbf, c_array  # Keep c_array in scope.


def is_canonical_triplicate_py(tt_values, dimension):
    vbf, _arr = _create_vbf_tt_from_list(tt_values, dimension)
    return bool(_check_lib.is_canonical_triplicate_c(ctypes.byref(vbf)))


def check_lin_equivalence_3to1_py(F_values, G_values, dimension):
    if len(F_values) != len(G_values):
        raise ValueError("F and G must have the same size (same dimension).")
    if (1 << dimension) != len(F_values):
        raise ValueError("Dimension mismatch with length(F_values).")

    vbfF, arrF = _create_vbf_tt_from_list(F_values, dimension)
    vbfG, arrG = _create_vbf_tt_from_list(G_values, dimension)

    # The check_lin_eq_2x_uniform_3to1 function expects both to be canonical triplicates.
    return bool(_check_lib.check_lin_eq_2x_uniform_3to1(ctypes.byref(vbfF), ctypes.byref(vbfG)))


# ----------------------------------------------------------------------------
# The Uniform3to1EquivalenceTest class (base_equivalence.py).
# ----------------------------------------------------------------------------
class Uniform3to1EquivalenceTest(EquivalenceTest):
    def are_equivalent(self, apnF, apnG):
        """
        Return True if both apnF and apnG are canonical triplicate (3-to-1),
        and are linearly equivalent. Return False otherwise.
        """
        # Check if dimension match.
        if apnF.field_n != apnG.field_n:
            return False

        dim = apnF.field_n
        # Get the Truth Table.
        F_tt = apnF._get_truth_table_list()
        G_tt = apnG._get_truth_table_list()

        # Check if both are canonical triplicate (3-to-1).
        if not is_canonical_triplicate_py(F_tt, dim):
            return False
        if not is_canonical_triplicate_py(G_tt, dim):
            return False

        # If both are canonical triplicate, check for linear equivalence using memory.
        return check_lin_equivalence_3to1_py(F_tt, G_tt, dim)