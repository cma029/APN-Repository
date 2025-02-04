# od_walsh_spectrum.py
# Description: Implementation of the Ortho-Derivative Walsh Spectrum (ODWS)

from computations.spectra.base_spectra import SpectraComputation
from c_spectra_bindings import vbf_tt_extended_walsh_spectrum_python

class ODWalshSpectrumComputation(SpectraComputation):
    """
    Ortho-Derivative Walsh Spectrum computation class.
    """

    def compute_spectrum(self, apn):
        # We obtain the APN's truth table as a Python list
        tt_values = apn._get_truth_table_list()
        dimension = apn.field_n

        # Then we call the C library function from spectra_computations.c,
        # which computes the extended Walsh spectrum.
        return vbf_tt_extended_walsh_spectrum_python(tt_values, dimension)