from __future__ import annotations
from computations.spectra.base_spectra import SpectraComputation
from c_spectra_bindings import vbf_tt_extended_walsh_spectrum
from vbf_object import VBF
from registry import REG

def _ensure_quadratic_flag(vbf_object: VBF) -> None:
    if "is_quadratic" in vbf_object.invariants:
        return
    try:
        is_quad_fn = REG.get("invariant", "is_quadratic")
        is_quad_fn(vbf_object)
    except Exception:
        pass

class ODWalshSpectrum(SpectraComputation):
    """
    Internal class for the Ortho-Derivative extended Walsh Spectrum (ODWS).
    """
    def compute_spectrum(self, vbf_object: VBF) -> dict | str:

        _ensure_quadratic_flag(vbf_object)
        if not vbf_object.invariants.get("is_quadratic", False):
            return "non-quadratic"

        tt_values = vbf_object._get_truth_table_list()

        # Call into the C-binding for the heavy-lifting.
        result = vbf_tt_extended_walsh_spectrum(tt_values, vbf_object.field_n)

        return {int(key): int(val) for key, val in result.items()}


@REG.register("invariant", "odws")
def odws_aggregator(vbf_object: VBF) -> None:
    # Aggregator function for 'odws'. Store into vbf_object.invariants["odws"].

    odws_spectrum = ODWalshSpectrum()
    result = odws_spectrum.compute_spectrum(vbf_object)
    vbf_object.invariants["odws"] = result