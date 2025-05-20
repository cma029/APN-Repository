from __future__ import annotations
from math import log2
from sage.all import Matrix, GF
from computations.rank.base_rank import RankComputation
from registry import REG

"""
Delta Rank implementations are adapted from the code provided in:
  L. Perrin, P. Q. Nguyen, E. B. Kavun, A. Biryukov, "sboxU: Tools for analyzing S-boxes"
  https://github.com/lpp-crypto/sboxU
We do not claim authorship of the original math. Big thanks to the authors.
"""

def oplus(x: int, y: int) -> int:
    return x ^ y

def ddt(func_tt_values: list[int]) -> list[list[int]]:
    """
    Compute the Difference Distribution Table (DDT) for the function F,
    where F is a list of length 2^n representing a truth table (0-based).
    DDT: ddt[a][b] = number of x such that f[x] ^ f[x XOR a] = b.
    """
    dimension_n = int(log2(len(func_tt_values)))
    size = 1 << dimension_n
    table = [[0]*size for _ in range(size)]
    for x in range(size):
        for a in range(size):
            diff = func_tt_values[x] ^ func_tt_values[x ^ a]
            table[a][diff] += 1
    return table

class DeltaRankComputation(RankComputation):
    """
    Implementation of the Delta-rank: build a 2^(2n) x 2^(2n) matrix, which is huge for n>8.
    """
    def compute_rank(self, vbf) -> int:
        # Limit dimensions > 8 for safety (adjust at own risk).
        if vbf.field_n > 8:
            raise ValueError("delta_rank is unsupported for dimension > 8")

        func_values = vbf._get_truth_table_list()
        n = vbf.field_n
        dimension = 1 << (2*n)

        # Build the Difference Distribution Table (DDT).
        table_ddt = ddt(func_values)

        # Collect all pairs (a,b) with table_ddt[a][b] == 2, skipping a=0.
        delta_pairs = []
        size = 1 << n
        for a in range(1, size):
            for b in range(size):
                if table_ddt[a][b] == 2:
                    delta_pairs.append((a << n) | b)

        # Build a 2^(2n) x 2^(2n) binary matrix.
        mat_content = []
        for x in range(dimension):
            row = [0]*dimension
            for pair_val in delta_pairs:
                row[oplus(x, pair_val)] = 1
            mat_content.append(row)

        mat_gf2 = Matrix(GF(2), dimension, dimension, mat_content)
        return mat_gf2.rank()


@REG.register("invariant", "delta_rank")
def delta_rank_aggregator(vbf):
    # Aggregator function for 'delta_rank'. Store into vbf.invariants["delta_rank"].

    # Limit dimensions > 8 for safety (adjust at own risk).
    if vbf.field_n > 8:
        vbf.invariants["delta_rank"] = None
        return

    # Instantiate the internal class and compute the rank.
    d_rank = DeltaRankComputation()
    computed_value = d_rank.compute_rank(vbf)
    vbf.invariants["delta_rank"] = computed_value