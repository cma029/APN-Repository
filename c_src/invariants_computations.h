/** invariants_computations.h
*
* C++ code adapted from ANSSI-FR/libapn (c) 2014-2018, authors including:
*   - Matthieu Rivain
*   - Solène Salvi
*   - ANSSI-FR  (https://github.com/ANSSI-FR/libapn)
*
* Extended/modified to support a user-specified irreducible polynomial
* bitmask for GF(2^n), enabling a real "is_monomial" check for n <= 16.
 */
 
#ifndef INVARIANTS_H
#define INVARIANTS_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void* function_t;

function_t create_function_from_truth_table(const uint32_t* table, unsigned int length);

/**
 * @param table   An array of length = 2^n for the function’s LUT.
 * @param length  The length of the table, i.e. 2^n.
 * @param poly    The integer bitmask of the irreducible polynomial for GF(2^n).
 *                The bitmask sets the bits for x^k where k is in the irr. polynomial.
 *                For example, if poly_str = "x^6 + x^4 + x^3 + x + 1", the bits for exponents {6,4,3,1,0}
 *                would be set, e.g. 0b01011011 = 0x5B. 
 */
function_t create_function_from_truth_table_and_poly(const uint32_t* table, unsigned int length, uint32_t poly);

void destroy_function(function_t f);

bool function_is_apn(function_t f);

unsigned int function_differential_uniformity(function_t f);

/**
 * Compute k-to-1. If the mapping is uniformly k-to-1, return k. If not, return -1.
 */
int function_k_to_1(function_t f);

unsigned int function_algebraic_degree(function_t f);

/**
 * If you call is_monomial without specifying a irr. polynomial, it will return False or fail.
 */
bool function_is_monomial(function_t f);

bool function_is_quadratic(function_t f);

#ifdef __cplusplus
}
#endif

#endif