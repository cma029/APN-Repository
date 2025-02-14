import ctypes
import os
import sys

if sys.platform.startswith('win'):
    lib_name = "libinvariants_computations.dll"
elif sys.platform.startswith('darwin'):
    lib_name = "libinvariants_computations.dylib"
else:
    lib_name = "libinvariants_computations.so"

lib_path = os.path.join(os.path.dirname(__file__), "c_src", lib_name)
lib_invariants = ctypes.CDLL(lib_path)

# -------------------------------------------------------------------------
# function_t-based invariants
# -------------------------------------------------------------------------

# function_t create_function_from_truth_table(const uint32_t* table, unsigned int length)
lib_invariants.create_function_from_truth_table.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint]
lib_invariants.create_function_from_truth_table.restype  = ctypes.c_void_p

# function_t create_function_from_truth_table_and_poly(const uint32_t*, unsigned int, uint32_t)
lib_invariants.create_function_from_truth_table_and_poly.argtypes = [
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.c_uint,
    ctypes.c_uint32
]
lib_invariants.create_function_from_truth_table_and_poly.restype  = ctypes.c_void_p

lib_invariants.destroy_function.argtypes = [ctypes.c_void_p]
lib_invariants.destroy_function.restype  = None

lib_invariants.function_is_apn.argtypes = [ctypes.c_void_p]
lib_invariants.function_is_apn.restype  = ctypes.c_bool

lib_invariants.function_differential_uniformity.argtypes = [ctypes.c_void_p]
lib_invariants.function_differential_uniformity.restype  = ctypes.c_uint

lib_invariants.function_k_to_1.argtypes = [ctypes.c_void_p]
lib_invariants.function_k_to_1.restype  = ctypes.c_int

lib_invariants.function_algebraic_degree.argtypes = [ctypes.c_void_p]
lib_invariants.function_algebraic_degree.restype  = ctypes.c_uint

lib_invariants.function_is_monomial.argtypes = [ctypes.c_void_p]
lib_invariants.function_is_monomial.restype  = ctypes.c_bool

lib_invariants.function_is_quadratic.argtypes = [ctypes.c_void_p]
lib_invariants.function_is_quadratic.restype  = ctypes.c_bool


def create_function_from_truth_table(tt):
    # Create a function_t handle from a truth table, ignoring polynomial (is_monomial won't be valid).
    arr_type = ctypes.c_uint32 * len(tt)
    arr = arr_type(*tt)
    return lib_invariants.create_function_from_truth_table(arr, len(tt))

def create_function_from_truth_table_and_poly(tt, poly_bits):
    # Create a function_t handle from a truth table and a user-provided irr. polynomial bitmask.
    #Example: poly_bits = 0x5B for x^6 + x^4 + x^3 + x + 1.
    arr_type = ctypes.c_uint32 * len(tt)
    arr = arr_type(*tt)
    return lib_invariants.create_function_from_truth_table_and_poly(arr, len(tt), poly_bits)

def destroy_function(func_ptr):
    lib_invariants.destroy_function(func_ptr)

def function_is_apn(func_ptr):
    return lib_invariants.function_is_apn(func_ptr)

def function_differential_uniformity(func_ptr):
    return lib_invariants.function_differential_uniformity(func_ptr)

def function_k_to_1(func_ptr):
    return lib_invariants.function_k_to_1(func_ptr)

def function_algebraic_degree(func_ptr):
    return lib_invariants.function_algebraic_degree(func_ptr)

def function_is_monomial(func_ptr):
    return lib_invariants.function_is_monomial(func_ptr)

def function_is_quadratic(func_ptr):
    return lib_invariants.function_is_quadratic(func_ptr)