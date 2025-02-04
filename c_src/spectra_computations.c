// spectra_computations.c
// Description: Implementation of the functions to compute the ODDS, ODWS, ect.

#include "spectra_computations.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>

/************************************************************************************************
 * The ODDS (Ortho-Derivative Differential Spectrum) and ODWS (Ortho-Derivative Walsh Spectrum)
 * computations are based on the work of Nikolay Stoyanov Kaleyski, whose code is available at:
 *
 * https://git.app.uib.no/Nikolay.Kaleyski/vectorial-boolean-functions
 *
 * These implementations follow or adapt the logic from that repository,
 * which we gratefully acknowledge.
 ************************************************************************************************/

/* Helper function to compute the dot product of two integers treated as bit vectors */
static bool dot_bits(unsigned long a, unsigned long b) {
    bool result = false;
    while (a || b) {
        bool bit_a = (a & 1);
        bool bit_b = (b & 1);
        result ^= (bit_a & bit_b);
        a >>= 1;
        b >>= 1;
    }
    return result;
}

static unsigned long o_xor(unsigned long x, unsigned long y) {
    return x ^ y;
}

/* Build orthoderivative */
static vbf_tt compute_orthoderivative(const vbf_tt *f) {
    vbf_tt od;
    od.vbf_tt_dimension = f->vbf_tt_dimension;
    od.vbf_tt_number_of_entries = f->vbf_tt_number_of_entries;

    od.vbf_tt_values = (vbf_tt_entry *) malloc(sizeof(vbf_tt_entry) * od.vbf_tt_number_of_entries);
    if (!od.vbf_tt_values) {
        fprintf(stderr, "[ERROR] Memory allocation failed for orthoderivative array.\n");
        exit(EXIT_FAILURE);
    }

    /* We set od(0) = 0 */
    memset(od.vbf_tt_values, 0, sizeof(vbf_tt_entry) * od.vbf_tt_number_of_entries);

    /* Compute each element of the ortho-derivative manually: o(a) must be such that
	 * the dot product od(a) * ( (F(0) + F(a) + F(x) + F(a+x) ) is equal to 0 for all x. */
    for (unsigned long a = 1; a < od.vbf_tt_number_of_entries; ++a) {
        bool orthogonal_found = false;
        for (unsigned long possible_value = 1; possible_value < od.vbf_tt_number_of_entries; ++possible_value) {
            bool is_orthogonal = true;
            for (unsigned long x = 0; x < od.vbf_tt_number_of_entries; ++x) {
                unsigned long derivative = f->vbf_tt_values[0]
                                         ^ f->vbf_tt_values[a]
                                         ^ f->vbf_tt_values[x]
                                         ^ f->vbf_tt_values[x ^ a];
                if (dot_bits(possible_value, derivative)) {
                    is_orthogonal = false;
                    break;
                }
            }
            if (is_orthogonal) {
                od.vbf_tt_values[a] = possible_value;
                orthogonal_found = true;
                break;
            }
        }
        if (!orthogonal_found) {
            /* No orthogonal found; set od(a)=0 */
            od.vbf_tt_values[a] = 0;
        }
    }

    return od;
}

/************************************************************************************************
 * Ortho-Derivative Differential Spectrum (ODDS)
 ************************************************************************************************/
void compute_differential_spectrum(const vbf_tt *f, size_t *spectrum_counts) {
    /* Compute orthoderivative */
    vbf_tt od = compute_orthoderivative(f);
    /* This will count the number of times each multiplicity is hit */
    size_t N  = od.vbf_tt_number_of_entries;

    memset(spectrum_counts, 0, sizeof(size_t) * (N + 1));
    /* This will count the number of different values in F(x) + F(a+x) for a fixed a */
    size_t *solutions = (size_t *)malloc(N * sizeof(size_t));
    if (!solutions) {
        fprintf(stderr, "[ERROR] Memory allocation for solutions[] failed.\n");
        free(od.vbf_tt_values);
        return;
    }

    for (size_t a = 1; a < N; ++a) {
        /* Reset solutions array for each a */
        memset(solutions, 0, N * sizeof(size_t));

        /* For each x, compute "hit" = od[x] ^ od[x^a] */
        for (size_t x = 0; x < N; ++x) {
            unsigned long hit = od.vbf_tt_values[x] ^ od.vbf_tt_values[x ^ a];
            ++solutions[hit];
        }

        /* Tally frequencies */
        for (size_t c = 0; c < N; ++c) {
            size_t freq = solutions[c];
            if (freq <= N) {
                spectrum_counts[freq]++;
            }
        }
    }

    free(solutions);
    free(od.vbf_tt_values);
}

/* Compute the Walsh transform */
static long walsh_transform(const vbf_tt *F, unsigned long a, unsigned long b) {
    long sum = 0;
    for (unsigned long x = 0; x < F->vbf_tt_number_of_entries; ++x) {
        bool exponent = dot_bits(a, x) ^ dot_bits(b, F->vbf_tt_values[x]);
        sum += exponent ? -1 : 1;
    }
    return sum;
}

/************************************************************************************************
 * Ortho-Derivative (extended) Walsh Spectrum (ODWS)
 ************************************************************************************************/
void compute_extended_walsh_spectrum(const vbf_tt *f, size_t *spectrum_counts) {
    /* Compute orthoderivative */
    vbf_tt od = compute_orthoderivative(f);
    /* All elements of the extended Walsh spectrum are non-negative, and upper bounded by 2^n, so
	 * we can proceed like in compute_differential_spectrum and have an array of counters. */
    size_t N  = od.vbf_tt_number_of_entries;

    /* Zero out the array for accumulation */
    memset(spectrum_counts, 0, sizeof(size_t) * (N + 1));

    /* For each (a,b), measure the Walsh transform of orthoderivative */
    for (unsigned long a = 0; a < N; ++a) {
        for (unsigned long b = 1; b < N; ++b) {
            long wc = walsh_transform(&od, a, b);
            size_t abs_wc = (wc >= 0) ? wc : -wc;
            if (abs_wc <= N) {
                spectrum_counts[abs_wc]++;
            } else {
                printf("[WARNING] abs_wc=%zu out-of-range (a=%lu,b=%lu)\n", abs_wc, a, b);
            }
        }
    }

    free(od.vbf_tt_values);
}