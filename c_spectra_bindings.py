# c_spectra_bindings.py
# Description: This file provides Python bindings to the C library
# that computes the ODDS, ODWS, ect.

import ctypes
import os
import sys
from ctypes import c_size_t, POINTER, c_ulong

if sys.platform.startswith('win'):
    lib_name = "spectra_computations.dll"
elif sys.platform.startswith('darwin'):
    lib_name = "libspectra_computations.dylib"
else:
    lib_name = "libspectra_computations.so"

lib_path = os.path.join(os.path.dirname(__file__), "c_src", lib_name)

spectra_lib = ctypes.CDLL(lib_path)

class VbfTt(ctypes.Structure):
    _fields_ = [
        ("vbf_tt_dimension", c_size_t),
        ("vbf_tt_number_of_entries", c_size_t),
        ("vbf_tt_values", POINTER(c_ulong)),
    ]

spectra_lib.compute_differential_spectrum.argtypes = [POINTER(VbfTt), POINTER(c_size_t)]
spectra_lib.compute_differential_spectrum.restype = None

spectra_lib.compute_extended_walsh_spectrum.argtypes = [POINTER(VbfTt), POINTER(c_size_t)]
spectra_lib.compute_extended_walsh_spectrum.restype = None

# --------------------------------------------------------------
# Internal helper to create the C structure from a Python list
# --------------------------------------------------------------
def create_vbf_tt_from_list(tt_values, dimension):
    num_entries = 1 << dimension
    if len(tt_values) != num_entries:
        raise ValueError(f"Truth table length {len(tt_values)} does not match 2^{dimension} = {num_entries}")

    ArrayType = c_ulong * num_entries
    c_array = ArrayType(*tt_values)

    vbf = VbfTt()
    vbf.vbf_tt_dimension = dimension
    vbf.vbf_tt_number_of_entries = num_entries
    vbf.vbf_tt_values = ctypes.cast(c_array, POINTER(c_ulong))

    return vbf, c_array

def vbf_tt_differential_spectrum_python(tt_values, dimension):
    vbf, c_array = create_vbf_tt_from_list(tt_values, dimension)

    spectrum_size = vbf.vbf_tt_number_of_entries + 1
    SpectrumArrayType = c_size_t * spectrum_size
    spectrum_counts = SpectrumArrayType()

    spectra_lib.compute_differential_spectrum(ctypes.byref(vbf), spectrum_counts)

    spectrum = {}
    for i in range(spectrum_size):
        if spectrum_counts[i] > 0:
            spectrum[i] = spectrum_counts[i]

    return spectrum

def vbf_tt_extended_walsh_spectrum_python(tt_values, dimension):
    vbf, c_array = create_vbf_tt_from_list(tt_values, dimension)

    spectrum_size = vbf.vbf_tt_number_of_entries + 1
    SpectrumArrayType = c_size_t * spectrum_size
    spectrum_counts = SpectrumArrayType()

    spectra_lib.compute_extended_walsh_spectrum(ctypes.byref(vbf), spectrum_counts)

    spectrum = {}
    for i in range(spectrum_size):
        if spectrum_counts[i] > 0:
            spectrum[i] = spectrum_counts[i]

    return spectrum