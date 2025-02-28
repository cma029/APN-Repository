#!/usr/bin/env python3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------------
# Default irreducible polynomials for n=2-32.
# --------------------------------------------------------------
DEFAULT_IRREDUCIBLE = {
    2:  0x7,         # x^2 + x + 1
    3:  0xB,         # x^3 + x + 1
    4:  0x13,        # x^4 + x + 1
    5:  0x25,        # x^5 + x^2 + 1
    6:  0x5B,        # x^6 + x^4 + x^3 + x + 1      (tested and verified)
    7:  0x83,        # x^7 + x + 1                  (tested and verified)
    8:  0x11D,       # x^8 + x^4 + x^3 + x^2 + 1    (tested and verified)
    9:  0x211,       # x^9 + x^4 + 1                (x^3 + x + 1 is also popular)
    10: 0x46F,       # x^10 + x^6 + x^5 + x^3 + x^2 + x + 1
    11: 0x805,       # x^11 + x^2 + 1
    12: 0x10EB,      # x^12 + x^7 + x^6 + x^5 + x^3 + x + 1
    13: 0x201B,      # x^13 + x^4 + x^3 + x + 1
    14: 0x40A9,      # x^14 + x^7 + x^5 + x^3 + 1
    15: 0x8035,      # x^15 + x^5 + x^4 + x^2 + 1
    16: 0x1002D,     # x^16 + x^5 + x^3 + x^2 + 1
    17: 0x20009,     # x^17 + x^3 + 1
    18: 0x41403,     # x^18 + x^12 + x^10 + x + 1
    19: 0x80027,     # x^19 + x^5 + x^2 + x + 1
    20: 0x1006F3,    # x^20 + x^10 + x^9 + x^7 + x^6 + x^5 + x^4 + x + 1
    21: 0x200065,    # x^21 + x^6 + x^5 + x^2 + 1
    22: 0x401F61,    # x^22 + x^12 + x^11 + x^10 + x^9 + x^8 + x^6 + x^5 + 1
    23: 0x800021,    # x^23 + x^5 + 1
    24: 0x101E6A9,   # x^24 + x^16 + x^15 + x^14 + x^13 + x^10 + x^9 + x^7 + x^5 + x^3 + 1
    25: 0x2000145,   # x^25 + x^8 + x^6 + x^2 + 1
    26: 0x40045D3,   # x^26 + x^14 + x^10 + x^8 + x^7 + x^6 + x^4 + x + 1
    27: 0x80016AD,   # x^27 + x^12 + x^10 + x^9 + x^7 + x^5 + x^3 + x^2 + 1
    28: 0x100020E5,  # x^28 + x^13 + x^7 + x^6 + x^5 + x^2 + 1
    29: 0x20000005,  # x^29 + x^2 + 1
    30: 0x400328AF,  # x^30 + x^17 + x^16 + x^13 + x^11 + x^7 + x^5 + x^3 + x^2 + x + 1
    31: 0x80000009,  # x^31 + x^3 + 1
    32: 0x100008299, # x^32 + x^15 + x^9 + x^7 + x^4 + x^3 + 1
}

# --------------------------------------------------------------
# Default generators for n=2-32.
# --------------------------------------------------------------
DEFAULT_GENERATOR = {
    2:  0x02,
    3:  0x02,
    4:  0x02,
    5:  0x02,
    6:  0x02,
    7:  0x02,
    8:  0x02, # AES uses 0x03.
    9:  0x02,
    10: 0x02,
    11: 0x02,
    12: 0x02,
    13: 0x02,
    14: 0x02,
    15: 0x02,
    16: 0x02,
    17: 0x02,
    18: 0x02,
    19: 0x02,
    20: 0x02,
    21: 0x02,
    22: 0x02,
    23: 0x02,
    24: 0x02,
    25: 0x02,
    26: 0x02,
    27: 0x02,
    28: 0x02,
    29: 0x02,
    30: 0x02,
    31: 0x02,
    32: 0x02,
}

# --------------------------------------------------------------
# Global variables.
# --------------------------------------------------------------
n = None
SIZE = 1 << n
REDUCTION_POLY = DEFAULT_IRREDUCIBLE[n]

gf_mul_table = []
gf_inv_table = []
gf_log = []
gf_alog = []

def gf_add(a, b):
    # Addition in GF(2^n) is XOR.
    return a ^ b

def gf_mul(a, b):
    # Multiply in GF(2^n) using precomputed table.
    return gf_mul_table[a][b]

def gf_inv(a):
    # Multiplicative inverse in GF(2^n).
    return gf_inv_table[a]

def build_tables(n, poly_int, generator):
    # Build multiplication/inverse/log tables using 'poly_int' and 'generator'.
    global SIZE, REDUCTION_POLY
    global gf_mul_table, gf_inv_table, gf_log, gf_alog

    SIZE = 1 << n
    REDUCTION_POLY = poly_int

    # Allocate tables.
    gf_mul_table = [[0]*SIZE for _ in range(SIZE)]
    gf_inv_table = [0]*SIZE
    gf_log = [0]*SIZE
    gf_alog = [0]*SIZE

    # Build multiplication table.
    for x in range(SIZE):
        for y in range(SIZE):
            gf_mul_table[x][y] = gf_mul_slow(x, y, n, poly_int)

    # Build inverse table.
    gf_inv_table[0] = 0
    for x in range(1, SIZE):
        gf_inv_table[x] = gf_find_inverse(x, n, poly_int)

    # Build discrete log with the chosen generator.
    build_log_tables(generator, n, poly_int)

def gf_mul_slow(a, b, n, poly_int):
    # Slow multiply in GF(2^n).
    r = 0
    for _ in range(n):
        if (b & 1) != 0:
            r ^= a
        b >>= 1
        carry = (a & (1 << (n-1))) != 0
        a <<= 1
        a &= ((1 << n) - 1)
        if carry:
            a ^= (poly_int & ((1 << n) - 1))
    return r

def gf_find_inverse(a, n, poly_int):
    # Find inverse of a in GF(2^n) using brute force.
    for x in range(1, (1 << n)):
        if gf_mul_slow(a, x, n, poly_int) == 1:
            return x
    return 0

def build_log_tables(generator, n, poly_int):
    # Build gf_log/gf_alog for the given generator.
    global gf_log, gf_alog
    size = (1 << n)

    gf_alog[0] = 1
    for k in range(1, size - 1):
        gf_alog[k] = gf_mul_slow(gf_alog[k-1], generator, n, poly_int)

    for x in range(size):
        gf_log[x] = 0
    for k in range(size - 1):
        x = gf_alog[k]
        gf_log[x] = k

# --------------------------------------------------------------
# Lagrange interpolation in GF(2^n)
# --------------------------------------------------------------

def interpolate_polynomial(sbox):
    """
    sbox: list of length SIZE
    returns poly[] of length SIZE: poly[i] is the coefficient of x^i
    """
    poly = [0]*SIZE

    for alpha in range(SIZE):
        y_alpha = sbox[alpha]
        if y_alpha == 0:
            continue

        # Build L_alpha.
        L = [0]*SIZE
        L[0] = 1
        for beta in range(SIZE):
            if beta == alpha:
                continue
            denom = gf_inv(gf_add(alpha, beta))
            L_new = [0]*SIZE
            # Multiply L by x => shift.
            for i in range(SIZE - 1):
                if L[i] != 0:
                    L_new[i+1] ^= L[i]
            # Multiply L by (-beta).
            for i in range(SIZE):
                if L[i] != 0:
                    L_new[i] ^= gf_mul(L[i], beta)
            # Multiply entire poly by denom.
            for i in range(SIZE):
                if L_new[i] != 0:
                    L_new[i] = gf_mul(L_new[i], denom)
            L = L_new

        # Accumulate y_alpha*L.
        for i in range(SIZE):
            if L[i] != 0:
                poly[i] ^= gf_mul(L[i], y_alpha)

    return poly

# --------------------------------------------------------------
# Convert polynomial to "g^k*x^i + ..." string.
# --------------------------------------------------------------

def coefficient_to_g_power(c):
    if c == 1:
        return "1"
    k = gf_log[c]
    return f"g^{k}"

def polynomial_to_string_g(coeffs):
    terms = []
    for i in reversed(range(SIZE)):
        c = coeffs[i]
        if c == 0:
            continue
        if c == 1:
            # "x^i" or "1".
            if i == 0:
                term = "1"
            elif i == 1:
                term = "x"
            else:
                term = f"x^{i}"
        else:
            coeff_str = coefficient_to_g_power(c)
            if i == 0:
                term = coeff_str
            elif i == 1:
                term = f"{coeff_str}*x"
            else:
                term = f"{coeff_str}*x^{i}"
        terms.append(term)

    if not terms:
        return "0"
    return " + ".join(terms)

# --------------------------------------------------------------
# Parsing each line and concurrency.
# --------------------------------------------------------------

def parse_sbox_line(line):
    line = line.strip()
    if line.endswith(","):
        line = line[:-1]
    line = line.strip("{}")
    parts = [p.strip() for p in line.split(",")]
    parts = [p for p in parts if p]
    if len(parts) != SIZE:
        raise ValueError(f"Expected {SIZE} decimal values, got {len(parts)}")
    return list(map(int, parts))

def process_sbox_line(idx, line):
    # Parse, then Interpolate, then Convert to string => Return (idx, poly_str).
    sbox = parse_sbox_line(line)
    poly = interpolate_polynomial(sbox)
    poly_str = polynomial_to_string_g(poly)
    return (idx, poly_str)

def main():
    # input_file = "bulk_import_7_test_tt.txt"
    # output_file = "bulk_import_7_test_apn.txt"

    input_file = "interpolation_GF2_8_test.tt.txt"
    output_file = "interpolation_GF2_8_test.apn.txt"
    

    with open(input_file, "r") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    # First line is the field n dimension.
    global n, SIZE, REDUCTION_POLY
    n = int(lines[0])
    if not (2 <= n <= 20):
        raise ValueError("n must be between 2 and 20.")

    # Default irreducible polynomial.
    if n not in DEFAULT_IRREDUCIBLE:
        raise ValueError(f"No default polynomial known for n={n}")
    poly_int = DEFAULT_IRREDUCIBLE[n]

    # Default generator.
    if n not in DEFAULT_GENERATOR:
        raise ValueError(f"No default generator known for n={n}")
    gen = DEFAULT_GENERATOR[n]

    # Build tables.
    build_tables(n, poly_int, gen)
    print(f"Using GF(2^{n}), irreducible_poly=0x{poly_int:X}, generator=0x{gen:X} (decimal {gen})")

    sbox_lines = lines[1:]
    SIZE = (1 << n)

    futures_map = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        for i, line in enumerate(sbox_lines, start=1):
            fut = executor.submit(process_sbox_line, i, line)
            futures_map[fut] = i

        results = []
        for fut in as_completed(futures_map):
            idx = futures_map[fut]
            line_idx, poly_str = fut.result()
            results.append((idx, poly_str))

    # Sort by index.
    results.sort(key=lambda x: x[0])

    # Print to file.
    with open(output_file, "w") as out:
        for (idx, poly_str) in results:
            out.write(f"{poly_str}\n")

    print(f"Done. Results in {output_file}")

if __name__ == "__main__":
    main()