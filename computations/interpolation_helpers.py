from computations.default_polynomials import DEFAULT_IRREDUCIBLE_POLYNOMIAL, DEFAULT_GENERATOR

# Global placeholders for GF(2^n) tables.
_gf_mul_table = []
_gf_inv_table = []
_gf_log_table = []
_gf_alog_table = []
_global_n = None
_global_poly_int = 0

def truth_table_to_univariate_poly(tt_values, field_n, irr_poly_int=0):
    """
    Convert a truth table (list of length 2^n) to a univariate polynomial representation 
    using Lagrange interpolation for finite fields over GF(2^n).
    """
    size = 1 << field_n
    if len(tt_values) != size:
        raise ValueError(
            f"Expected {size} elements for dimension {field_n}, received {len(tt_values)}."
        )

    # If we do not have a user supplied irreducible polynomial, then fallback.
    if irr_poly_int == 0:
        if field_n not in DEFAULT_IRREDUCIBLE_POLYNOMIAL:
            raise ValueError(f"No default irreducible polynomial provided for n={field_n}.")
        irr_poly_int = DEFAULT_IRREDUCIBLE_POLYNOMIAL[field_n]

    # Fetch the default generator.
    if field_n not in DEFAULT_GENERATOR:
        raise ValueError(f"No default generator provided for n={field_n}.")
    generator = DEFAULT_GENERATOR[field_n]

    _build_all_tables(field_n, irr_poly_int, generator)

    coefficients = _lagrange_interpolation(tt_values)

    # Build the polynomial terms (coefficient_exp, monomial_exp).
    result_terms = []
    for i in range(size):
        current = coefficients[i]
        if current != 0:
            coeff_exp = _gf_log_table[current]
            mon_exp = i
            result_terms.append((coeff_exp, mon_exp))

    return (result_terms, irr_poly_int)


def _build_all_tables(field_n, poly_int, generator):
    global _global_n, _global_poly_int
    global _gf_mul_table, _gf_inv_table, _gf_log_table, _gf_alog_table

    _global_n = field_n
    _global_poly_int = poly_int
    size = 1 << field_n

    _gf_mul_table = [[0]*size for _ in range(size)]
    _gf_inv_table = [0]*size
    _gf_log_table = [0]*size
    _gf_alog_table = [0]*size

    for x in range(size):
        for y in range(size):
            _gf_mul_table[x][y] = _gf_mul_slow(x, y, field_n, poly_int)

    _gf_inv_table[0] = 0
    for x in range(1, size):
        _gf_inv_table[x] = _gf_find_inverse(x, field_n, poly_int)

    _build_log_tables(generator, field_n, poly_int)


def _lagrange_interpolation(tt_values):
    size = len(tt_values)
    poly = [0]*size

    for alpha in range(size):
        y_alpha = tt_values[alpha]
        if y_alpha == 0:
            continue

        # Build L_alpha.
        L = [0]*size
        L[0] = 1
        for beta in range(size):
            if beta == alpha:
                continue
            denominator = _gf_inv(_gf_add(alpha, beta))

            L_new = [0]*size

            # Multiply L(x) by (x + beta).
            #   => shift up by 1 for multiply by x.
            #   => XOR with beta for each index where L[i]!=0.
            for i in range(size - 1):
                if L[i] != 0:
                    L_new[i+1] ^= L[i]
            for i in range(size):
                if L[i] != 0:
                    L_new[i] ^= _gf_mul(L[i], beta)

            # Multiply the entire polynomial by denominator.
            for i in range(size):
                if L_new[i] != 0:
                    L_new[i] = _gf_mul(L_new[i], denominator)

            L = L_new

        # Accumulate y_alpha * L into poly.
        for i in range(size):
            if L[i] != 0:
                poly[i] ^= _gf_mul(L[i], y_alpha)

    return poly


def _gf_add(a, b):
    # Addition in GF(2^n) is just XOR.
    return a ^ b


def _gf_mul(a, b):
    # Use the global table for multiplication.
    return _gf_mul_table[a][b]


def _gf_inv(a):
    # Use the global inverse table.
    return _gf_inv_table[a]


def _gf_mul_slow(a, b, field_n, poly_int):
    """
    Slow GF(2^n) multiplication using the Russian-peasant approach.
    Bitwise multiply a,b in GF(2^n), reduce by poly_int.
    """
    r = 0
    for _ in range(field_n):
        if (b & 1) != 0:
            r ^= a
        b >>= 1
        carry = (a & (1 << (field_n-1))) != 0
        a <<= 1
        a &= ((1 << field_n) - 1)
        if carry:
            a ^= (poly_int & ((1 << field_n) - 1))
    return r


def _gf_find_inverse(a, field_n, poly_int):
    # Brute force: find x in [1..(1<<n)-1] such that a*x=1.
    if a == 0:
        return 0
    size = 1 << field_n
    for x in range(1, size):
        if _gf_mul_slow(a, x, field_n, poly_int) == 1:
            return x
    return 0


def _build_log_tables(generator, field_n, poly_int):
    # Build discrete alog and log for alpha=generator in GF(2^n).
    global _gf_log_table, _gf_alog_table

    size = 1 << field_n

    _gf_alog_table[0] = 1
    for k in range(1, size - 1):
        _gf_alog_table[k] = _gf_mul_slow(_gf_alog_table[k-1], generator, field_n, poly_int)

    for x in range(size):
        _gf_log_table[x] = 0
    for k in range(size - 1):
        val = _gf_alog_table[k]
        _gf_log_table[val] = k