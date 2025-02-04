#ifndef SPECTRA_COMPUTATIONS_H
#define SPECTRA_COMPUTATIONS_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>
#include <stdbool.h>

#ifdef _WIN32
  #define EXPORT __declspec(dllexport)
#else
  #define EXPORT
#endif

typedef unsigned long vbf_tt_entry;

typedef struct vbf_truth_table {
    size_t vbf_tt_dimension;
    size_t vbf_tt_number_of_entries;
    vbf_tt_entry* vbf_tt_values;
} vbf_tt;

/* Compute_extended_walsh_spectrum: Ortho-Derivative Walsh Spectrum (ODWS) */
EXPORT void compute_extended_walsh_spectrum(const vbf_tt* f, size_t* spectrum_counts);

/* Compute_differential_spectrum: Ortho-Derivative Differential Spectrum (ODDS) */
EXPORT void compute_differential_spectrum(const vbf_tt* f, size_t* spectrum_counts);

#ifdef __cplusplus
}
#endif

#endif