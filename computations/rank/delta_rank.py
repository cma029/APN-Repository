# delta_rank.py
# Description: This file contains the implementation of the Delta-rank.

from sage.all import Matrix, GF, log
from computations.rank.base_rank import RankComputation
from computations.rank.gamma_rank import oplus

def ddt(f):
    # Compute the Difference Distribution Table (DDT) for the function f,
    # where f is a list of length 2^n representing a LUT (0-based).

    # ddt[a][b] = number of x such that f[x] ^ f[x XOR a] = b.
    n = int(log(len(f), 2))
    size = 1 << n
    table = [[0]*size for _ in range(size)]

    for x in range(size):
        for a in range(size):
            diff = f[x] ^ f[x ^ a]
            table[a][diff] += 1

    return table

class DeltaRankComputation(RankComputation):
    def compute_rank(self, apn):
        f = apn._get_truth_table_list()
        n = int(log(len(f), 2))
        dim = 1 << (2*n)

        # 1) Compute DDT.
        table = ddt(f)

        # 2) Collect all pairs (a,b) where table[a][b] == 2, skipping a=0.
        delta_pairs = []
        for a in range(1, 1 << n):
            for b in range(1 << n):
                if table[a][b] == 2:
                    delta_pairs.append((a << n) | b)

        # 3) Build the binary matrix.
        mat_content = []
        for x in range(dim):
            row = [0]*dim
            for y in delta_pairs:
                row[oplus(x, y)] = 1
            mat_content.append(row)

        # 4) Convert to Sage matrix over GF(2) and compute rank.
        mat_gf2 = Matrix(GF(2), dim, dim, mat_content)
        return mat_gf2.rank()