# apn_test.py
# Description: Test file for APN class and its methods.

from abc import ABC, abstractmethod

class DifferentialUniformity(ABC):
    @abstractmethod
    def is_usable(self, apn):
        pass

    @abstractmethod
    def compute(self, apn):
        pass

class BasicDUMethod(DifferentialUniformity):
    def is_usable(self, apn):
        # We need a way to select the best algorithm from invariants. Return true for now.
        return True

    def compute(self, apn):
        # Check if we have a truth table representation
        if not hasattr(apn.representation, 'truth_table'):
            # Get a new APN with truth table representation
            apn_tt = apn.get_truth_table()
        else:
            # APN has truth table representation (good to go).
            apn_tt = apn

        tt = apn_tt.representation.truth_table
        n = apn_tt.field_n
        field_size = 2**n

        # Method from INF143A
        max_solutions = 0
        # For each nonzero a
        for a in range(1, field_size):
            # For each b
            for b in range(field_size):
                count_solutions = 0
                # Count solutions to f(x) + f(a + x) = b
                # Addition in GF(2^n) when represented by integers is XOR (we use ^)
                for x in range(field_size):
                    x_xor_a = x ^ a
                    if (tt[x] ^ tt[x_xor_a]) == b:
                        count_solutions += 1
                if count_solutions > max_solutions:
                    max_solutions = count_solutions

        # Returns the differential uniformity value (int).
        return max_solutions

class DifferentialUniformityComputer:
    def __init__(self, methods=None):
        # We should have "basic_method" as default
        if methods is None:
            methods = [BasicDUMethod()]
        self.methods = methods

    def compute_du(self, apn):
        # Compute the differential uniformity
        for method in self.methods:
            if method.is_usable(apn):
                return method.compute(apn)
        # Just in case no suitable method is found
        raise ValueError("No suitable method found for computing differential uniformity.")