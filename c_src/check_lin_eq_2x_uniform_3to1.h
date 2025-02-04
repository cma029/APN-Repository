#ifndef CHECK_LIN_EQ_2X_UNIFORM_3TO1_H
#define CHECK_LIN_EQ_2X_UNIFORM_3TO1_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdbool.h>
#include <stddef.h>

typedef struct vbf_truth_table {
    size_t vbf_tt_dimension;
    size_t vbf_tt_number_of_entries;
    unsigned long *vbf_tt_values;
} vbf_tt;

/* Returns true if F is a uniform 3-to-1 function (triplicate). */
bool is_canonical_triplicate_c(vbf_tt *F);

/* Returns true if F and G are linearly equivalent uniform 3-to-1 functions. */
bool check_lin_eq_2x_uniform_3to1(vbf_tt *F, vbf_tt *G);

#ifdef __cplusplus
}
#endif

#endif