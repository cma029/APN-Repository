# is_quadratic_apn.py
# Description: Determines whether a given Almost Perfect Nonlinear (APN) 
# function is quadratic based on its truth table.

def mobius_transform(f):
    # Computes the Möbius transform (ANF coefficients) of a Boolean function.
    n = len(f).bit_length() - 1
    f = f.copy()
    for i in range(n):
        for mask in range(2**n):
            if mask & (1 << i):
                f[mask] ^= f[mask ^ (1 << i)]
    return f

def get_degree(anf_coeffs, n):
    # Computes the algebraic degree of a Boolean function from its ANF coefficients.
    max_deg = 0
    for mask, coeff in enumerate(anf_coeffs):
        if coeff:
            deg = bin(mask).count('1')
            if deg > max_deg:
                max_deg = deg
    return max_deg

def is_quadratic_apn(truth_table, n):
    # Determines if the given APN function F: GF(2^n) -> GF(2^n) is quadratic.
    if not isinstance(truth_table, (list, tuple)):
        raise TypeError("truth_table must be a list or tuple of integers.")
    
    expected_length = 2**n
    if len(truth_table) != expected_length:
        raise ValueError(f"truth_table length must be {expected_length} for n={n}.")
    
    max_output = 2**n - 1
    for idx, output in enumerate(truth_table):
        if not isinstance(output, int):
            raise ValueError(f"All elements in truth_table must be integers. Found {type(output)} at index {idx}.")
        if not (0 <= output <= max_output):
            raise ValueError(f"Each element in truth_table must be between 0 and {max_output}. Found {output} at index {idx}.")

    max_degree = 0

    for i in range(n):
        component_truth_table = [(output >> i) & 1 for output in truth_table]
        anf_coeffs = mobius_transform(component_truth_table)
        degree = get_degree(anf_coeffs, n)
        if degree > max_degree:
            max_degree = degree
        if max_degree > 2:
            return False

    return max_degree <= 2