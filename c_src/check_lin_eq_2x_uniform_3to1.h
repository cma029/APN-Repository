/*********************************************************************************/
/*  check_lin_eq_2x_uniform_3to1.h                                               */
/*                                                                               */
/*  Adapted from the "nskal/tripeq" repository at:                               */
/*    https://github.com/nskal/tripeq/tree/main                                  */
/*  Contributors to tripeq include: Ivana Ivkovic and Nikolay Stoyanov Kaleyski. */
/*                                                                               */
/*  Provides function prototypes for checking whether a function is a            */
/*  canonical 3-to-1 triplicate, and for running the linear equivalence          */
/*  check on two canonical 3-to-1 functions.                                     */
/*                                                                               */
/*********************************************************************************/

#ifndef CHECK_LIN_EQ_2X_UNIFORM_3TO1_H
#define CHECK_LIN_EQ_2X_UNIFORM_3TO1_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdbool.h>
#include <stddef.h>

/*
 * Minimal definitions from vbf.h to support usage of vbf_tt in memory.
 */

typedef unsigned long vbf_tt_entry;

typedef struct vbf_truth_table {
    size_t vbf_tt_dimension;
    size_t vbf_tt_number_of_entries;
    vbf_tt_entry *vbf_tt_values;
} vbf_tt;

/*
 * Checks whether the provided function F is a canonical triplicate (3-to-1)
 * function in even dimension >= 4. Returns 'True' if yes, 'False' otherwise.
 */
bool is_canonical_triplicate_c(vbf_tt *F);

/*
 * Checks if two canonical 3-to-1 functions F and G (same dimension) are
 * linearly equivalent. Returns 'True' if yes, 'False' otherwise.
 */
bool check_lin_eq_2x_uniform_3to1(vbf_tt *F, vbf_tt *G);

#ifdef __cplusplus
}
#endif

#endif