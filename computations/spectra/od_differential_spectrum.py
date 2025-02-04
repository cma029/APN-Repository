# od_differential_spectrum.py
# Description: Implementation of the Ortho-Derivative Differential Spectrum (ODDS)

from computations.spectra.base_spectra import SpectraComputation
from c_spectra_bindings import vbf_tt_differential_spectrum_python

class ODDifferentialSpectrumComputation(SpectraComputation):
    """
    Ortho-Derivative Differential Spectrum computation class.
    """

    def compute_spectrum(self, apn):
        # We obtain the APN's truth table as a Python list
        tt_values = apn._get_truth_table_list()
        dimension = apn.field_n

        # Then we call the C library function from spectra_computations.c,
        # which computes the OD differential spectrum.
        return vbf_tt_differential_spectrum_python(tt_values, dimension)