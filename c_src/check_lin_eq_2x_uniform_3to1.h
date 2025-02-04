#ifndef CHECK_LIN_EQ_2X_UNIFORM_3TO1_H
#define CHECK_LIN_EQ_2X_UNIFORM_3TO1_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdbool.h>
#include <stddef.h>

// vbf_tt structure
typedef struct vbf_truth_table {
    size_t vbf_tt_dimension;
    size_t vbf_tt_number_of_entries;
    unsigned long *vbf_tt_values;
} vbf_tt;

bool is_canonical_triplicate_c(vbf_tt *F);

bool check_lin_eq_2x_uniform_3to1(vbf_tt *F, vbf_tt *G);

#ifdef __cplusplus
}
#endif

#endif