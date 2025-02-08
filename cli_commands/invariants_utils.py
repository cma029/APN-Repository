from apn_object import APN
from computations.rank.delta_rank import DeltaRankComputation
from computations.rank.gamma_rank import GammaRankComputation
from computations.spectra.od_differential_spectrum import ODDifferentialSpectrumComputation
from computations.spectra.od_walsh_spectrum import ODWalshSpectrumComputation

def compute_apn_invariants(apn: APN):
    # Sets the invariants in apn.invariants.
    try:
        apn_tt = apn.get_truth_table()
        tt = apn_tt.representation.truth_table
    except Exception:
        return

    # Delta Rank
    try:
        d_rank = DeltaRankComputation().compute_rank(apn_tt)
        apn.invariants["delta_rank"] = d_rank
    except Exception:
        apn.invariants["delta_rank"] = None

    # Gamma Rank
    try:
        g_rank = GammaRankComputation().compute_rank(apn_tt)
        apn.invariants["gamma_rank"] = g_rank
    except Exception:
        apn.invariants["gamma_rank"] = None

    # If is_quadratic, compute Ortho-Derivative Spectras.
    is_quad = apn.properties.get("is_quadratic", False)
    if is_quad:
        try:
            odds_res = ODDifferentialSpectrumComputation().compute_spectrum(apn_tt)
            apn.invariants["odds"] = {int(k): int(v) for k, v in odds_res.items()}
        except Exception:
            apn.invariants["odds"] = "non-quadratic"

        try:
            odws_res = ODWalshSpectrumComputation().compute_spectrum(apn_tt)
            apn.invariants["odws"] = {int(k): int(v) for k, v in odws_res.items()}
        except Exception:
            apn.invariants["odws"] = "non-quadratic"
    else:
        apn.invariants["odds"] = "non-quadratic"
        apn.invariants["odws"] = "non-quadratic"