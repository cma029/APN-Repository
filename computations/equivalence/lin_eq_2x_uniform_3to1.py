# lin_eq_2x_uniform_3to1.py
# Description: linear equivalence test for testing two uniform 3-to-1 APNs.

from computations.equivalence.base_equivalence import EquivalenceTest

def check_2x_uniform_3to1_equivalence_python(ttF, nF, ttG, nG):
    from check_lin_eq_2x_uniform_3to1 import check_lin_eq_2x_uniform_3to1_python
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