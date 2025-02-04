# gamma_rank.py
# Description: This file contains the implementation of the Gamma-rank

from sage.all import Matrix, GF, log
from computations.rank.base_rank import RankComputation

"""
Gamma Rank implementations are adapted from the code provided in:

L. Perrin, P. Q. Nguyen, E. B. Kavun, A. Biryukov, "sboxU: Tools for analyzing S-boxes,"
available at https://github.com/lpp-crypto/sboxU

All code logic herein is implemented in accordance with the algorithms/design
shared in sboxU. We do not claim authorship of the original mathematics.
We thank the original authors for making their code available.
"""

def oplus(x, y):
    # Bitwise XOR function
    return x ^ y

class GammaRankComputation(RankComputation):
    # Implementation of the Gamma-rank.
    def compute_rank(self, apn):
        f = apn._get_truth_table_list()
        n = int(log(len(f), 2))
        dim = 1 << (2*n)

        # Build the Gamma set
        gamma = [((x << n) | f[x]) for x in range(1 << n)]

        # Build the binary matrix content in Python
        mat_content = []
        for x in range(dim):
            row = [0]*dim
            for y in gamma:
                row[oplus(x, y)] = 1
            mat_content.append(row)

        # Convert to Sage matrix over GF(2) and compute rank
        mat_gf2 = Matrix(GF(2), dim, dim, mat_content)
        return mat_gf2.rank()