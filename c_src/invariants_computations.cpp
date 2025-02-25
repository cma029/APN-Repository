// invariants_computations.cpp
//
// C++ code adapted from ANSSI-FR/libapn (c) 2014-2018, authors including:
//   - Matthieu Rivain
//   - Solène Salvi
//   - ANSSI-FR  (https://github.com/ANSSI-FR/libapn)
//
// Extended/modified to support a user-specified irreducible polynomial
// bitmask for GF(2^n), enabling a real "is_monomial" check for n <= 16.
//
// This code computes:
//   - APN check & Differential uniformity.
//   - k-to-1 property.
//   - ANF =>
//      - Algebraic degree.
//      - is_monomial (F(x) = a*x^d + b) in GF(2^n).
//      - is_quadratic.
//
// -----------------------------------------------------------------------------

#include "invariants_computations.h"

#include <vector>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <limits>

// -----------------------------------------------------------------------------
// Struct to store the function LUT + irreducible polynomial.
// -----------------------------------------------------------------------------
struct Function {
    std::vector<uint32_t> LUT; // The function's truth table: F(x) = LUT[x].
    uint32_t polynomial;       // Bitmask for irreducible polynomial (0 if none).
    unsigned int n;            // Dimension n (such that size = 2^n).

    Function() : polynomial(0), n(0) {}
};

// Minimal RAII wrapper to store a Function* in function_t handle.
struct FunctionHandle {
    Function* func;
};

// -----------------------------------------------------------------------------
// Helper: compute dimension n from LUT size.
// -----------------------------------------------------------------------------
static unsigned int lut_dimension(unsigned int length) {
    // Length = 2^n => n = log2(length).
    unsigned int n = 0;
    while (length > 1) {
        if ((length & 1) != 0) return 0; // Not a power of two => error.
        length >>= 1;
        n++;
    }
    return n;
}

// -----------------------------------------------------------------------------
// Creating or destroying a function.
// -----------------------------------------------------------------------------
extern "C" function_t
create_function_from_truth_table(const uint32_t* table, unsigned int length)
{
    if (!table || length == 0) {
        return nullptr;
    }
    // Check dimension.
    unsigned int n = lut_dimension(length);
    if ((1U << n) == 0) {
        // Error.
        return nullptr;
    }

    Function* f = new Function();
    f->LUT.assign(table, table + length);
    f->n = n;
    f->polynomial = 0; // No irreducible polynomial from the user.

    FunctionHandle* h = new FunctionHandle();
    h->func = f;
    return reinterpret_cast<function_t>(h);
}

extern "C" function_t
create_function_from_truth_table_and_poly(const uint32_t* table, unsigned int length, uint32_t poly)
{
    if (!table || length == 0) {
        return nullptr;
    }
    unsigned int n = lut_dimension(length);
    if ((1U << n) == 0) {
        return nullptr;
    }

    Function* f = new Function();
    f->LUT.assign(table, table + length);
    f->n = n;
    f->polynomial = poly; // Store user-specified irreducible polynomial.

    FunctionHandle* h = new FunctionHandle();
    h->func = f;
    return reinterpret_cast<function_t>(h);
}

extern "C" void
destroy_function(function_t fh)
{
    if (!fh) return;
    FunctionHandle* handle = reinterpret_cast<FunctionHandle*>(fh);
    if (handle->func) {
        delete handle->func;
        handle->func = nullptr;
    }
    delete handle;
}

// -----------------------------------------------------------------------------
// APN check & Differential uniformity.
// -----------------------------------------------------------------------------
static unsigned int differential_uniformity(const Function& F)
{
    if (F.n == 0) return 0;
    unsigned int sz = 1U << F.n;
    const auto& LUT = F.LUT;

    std::vector<unsigned int> ddt(sz * sz, 0);
    for (unsigned int x = 0; x < sz; x++) {
        for (unsigned int a = 0; a < sz; a++) {
            unsigned int y = x ^ a;
            unsigned int out_diff = LUT[x] ^ LUT[y];
            ddt[a * sz + out_diff]++;
        }
    }

    // Find max count among a != 0.
    unsigned int max_count = 0;
    for (unsigned int a = 1; a < sz; a++) {
        for (unsigned int b = 0; b < sz; b++) {
            if (ddt[a * sz + b] > max_count) {
                max_count = ddt[a * sz + b];
            }
        }
    }
    return max_count;
}
static bool is_apn(const Function& F)
{
    return (differential_uniformity(F) == 2);
}

extern "C" bool
function_is_apn(function_t fh)
{
    if (!fh) return false;
    FunctionHandle* handle = reinterpret_cast<FunctionHandle*>(fh);
    return is_apn(*handle->func);
}

extern "C" unsigned int
function_differential_uniformity(function_t fh)
{
    if (!fh) return 0;
    FunctionHandle* handle = reinterpret_cast<FunctionHandle*>(fh);
    return differential_uniformity(*handle->func);
}

// -----------------------------------------------------------------------------
// Compute the k-to-1 (inspired by the frequency-counting logic used in libapn).
// -----------------------------------------------------------------------------
static int compute_k_to_1(const Function& F)
{
    if (F.n == 0) {
        // Edge case: only 1 possible input => output is LUT[0].
        // If LUT[0] == 0, we have 0->0 => that is trivially 1-to-1, so return 1.
        // Otherwise, if LUT[0] != 0, that breaks the “only 0 -> 0” assumption.
        if (F.LUT[0] == 0)
            return 1;
        else
            return -1;
    }

    unsigned int sz = 1U << F.n;
    const auto& LUT = F.LUT;

    // Count frequencies.
    std::vector<unsigned int> freq(sz, 0);
    for (unsigned int x = 0; x < sz; x++) {
        unsigned int outv = LUT[x];
        if (outv >= sz) {
            // Out of range. Can’t be valid under GF(2^n).
            return -1;
        }
        freq[outv]++;
    }

    // Enforce “0 -> 0” => freq[0] == 1.
    if (freq[0] != 1) {
        return -1;
    }

    // Find k among nonzero outputs.
    int k = -1;
    for (unsigned int v = 1; v < sz; v++) {
        if (freq[v] > 0) {
            k = (int)freq[v];
            break;
        }
    }
    if (k < 0) {
        // k < 0 means no nonzero output and everything mapped to 0.
        return -1;
    }

    // Check that all nonzero outputs have the same frequency k.
    for (unsigned int v = 1; v < sz; v++) {
        if (freq[v] != 0 && (int)freq[v] != k) {
            return -1; // Mismatch => not k-to-1.
        }
    }

    return k;
}

extern "C" int
function_k_to_1(function_t fh)
{
    if (!fh) return -1;
    FunctionHandle* handle = reinterpret_cast<FunctionHandle*>(fh);
    return compute_k_to_1(*handle->func);
}

// -----------------------------------------------------------------------------
// Algebraic Normal Form (ANF) for multi-variate => algebraic degree.
// -----------------------------------------------------------------------------
static void compute_anf_bool_inplace(std::vector<uint8_t>& f)
{
    unsigned int sz = f.size();
    for (unsigned int step = 1; step < sz; step <<= 1) {
        for (unsigned int j = 0; j < sz; j++) {
            if ((j & step) != 0) {
                f[j] ^= f[j ^ step];
            }
        }
    }
}

static unsigned int compute_algebraic_degree_mv(const Function& F)
{
    if (F.n == 0) return 0;
    unsigned int sz = 1U << F.n;
    const auto& LUT = F.LUT;

    // Coordinate-by-coordinate.
    std::vector< std::vector<uint8_t> > anf(F.n);
    for (unsigned int c = 0; c < F.n; c++) {
        anf[c].resize(sz);
        for (unsigned int x = 0; x < sz; x++) {
            uint32_t outv = LUT[x];
            uint8_t bit_c = (uint8_t)((outv >> c) & 1);
            anf[c][x] = bit_c;
        }
        compute_anf_bool_inplace(anf[c]);
    }

    // Find max degree across coordinates.
    unsigned int max_deg = 0;
    for (unsigned int c = 0; c < F.n; c++) {
        for (int i = (int)sz - 1; i >= 0; i--) {
            if (anf[c][i] == 1) {
                // Popcount.
                unsigned int tmp = (unsigned int)i;
                unsigned int w = 0;
                while (tmp) {
                    w += (tmp & 1);
                    tmp >>= 1;
                }
                if (w > max_deg) {
                    max_deg = w;
                }
                break; // Next coordinate.
            }
        }
    }
    return max_deg;
}

extern "C" unsigned int
function_algebraic_degree(function_t fh)
{
    if (!fh) return 0;
    FunctionHandle* handle = reinterpret_cast<FunctionHandle*>(fh);
    return compute_algebraic_degree_mv(*handle->func);
}

// -----------------------------------------------------------------------------
// Quadratic => algebraic_degree = 2.
// -----------------------------------------------------------------------------
static bool is_quadratic(const Function& F)
{
    unsigned int deg = compute_algebraic_degree_mv(F);
    return (deg == 2);
}

extern "C" bool
function_is_quadratic(function_t fh)
{
    if (!fh) return false;
    FunctionHandle* handle = reinterpret_cast<FunctionHandle*>(fh);
    return is_quadratic(*handle->func);
}

// -----------------------------------------------------------------------------
// Compute: is_monomial => F(x) = a*x^d + b in GF(2^n).
//  - Code rely on the user-provided irr. polynomial bitmask (F.polynomial).
//  - If poly=0 or n>16 => return False (not handled).
//  - We do a naive exponent search in [0..2^n-2] & check all x.
//
//  WARNING: For n=16, this can be very slow in worst-case ~4+ billion checks.
// -----------------------------------------------------------------------------
static inline unsigned int bitcount(unsigned int x)
{
    // Quick popcount (portable):
    unsigned int w = 0;
    while (x) {
        w += (x & 1);
        x >>= 1;
    }
    return w;
}

// Build log/antilog with the irr. polynomial bitmask. 2^n up to 65536.
struct GF2nCtx {
    unsigned int n;
    unsigned int size; // 2^n.
    std::vector<unsigned int> logtbl;   // Length = size.
    std::vector<unsigned int> alogtbl;  // Length = size.
    uint32_t poly; // Bitmask.

    GF2nCtx(unsigned int n_, uint32_t poly_) : n(n_), size(1U << n_), poly(poly_) {
        logtbl.resize(size, 0);
        alogtbl.resize(size, 0);
        build_tables();
    }

    void build_tables() {
        // Treat "alpha" = 0x2. Then if shifting out of range, XOR with irr. poly.
        // We assume the highest set bit in poly is x^n.
        // Skip verifying that it is indeed primitive, and we trust the user’s polynomial.

        alogtbl[0] = 1; // alpha^0 = 1.
        for (unsigned int i = 1; i < size - 1; i++) {
            unsigned int prev = alogtbl[i - 1];
            unsigned int next = (prev << 1);
            // If next's (n)th bit is set, reduce with irr. poly.
            if ((next & (1U << n)) != 0) {
                next ^= poly;
            }
            alogtbl[i] = next;
        }
        // Fill log table.
        for (unsigned int i = 0; i < size - 1; i++) {
            unsigned int v = alogtbl[i];
            logtbl[v] = i;
        }
    }
};

static inline unsigned int gf_mul(const GF2nCtx &ctx, unsigned int x, unsigned int y)
{
    if (x == 0 || y == 0) return 0;
    unsigned int lx = ctx.logtbl[x];
    unsigned int ly = ctx.logtbl[y];
    unsigned int s = lx + ly;
    s %= (ctx.size - 1);
    return ctx.alogtbl[s];
}
static inline unsigned int gf_pow(const GF2nCtx &ctx, unsigned int x, unsigned int d)
{
    if (x == 0) {
        // 0^d = 0 if d>0, else 1 if d=0.
        return (d == 0) ? 1 : 0;
    }
    unsigned int lx = ctx.logtbl[x];
    unsigned int e = (lx * d) % (ctx.size - 1);
    return ctx.alogtbl[e];
}

static bool is_monomial_impl(const Function& F)
{
    // If polynomial=0, we have no GF definition => False.
    // If n>16 => skip due to performance or no support.
    if (F.polynomial == 0) return false;
    if (F.n > 16) return false;

    unsigned int sz = 1U << F.n;
    const auto& LUT = F.LUT;
    GF2nCtx ctx(F.n, F.polynomial);

    // b = F(0).
    unsigned int b = LUT[0];
    // Check if constant => if all LUT[x] == b => not a monomial with nonzero 'a'.
    {
        bool all_same = true;
        for (unsigned int x = 0; x < sz; x++) {
            if (LUT[x] != b) {
                all_same = false;
                break;
            }
        }
        if (all_same) {
            return false; // Purely constant => no.
        }
    }

    // For d in [0..(sz-2)], try to find a => check.
    for (unsigned int d = 0; d < (sz - 1); d++) {
        bool found_candidate_a = false;
        // Pick x=1..(sz-1), see if x^d != 0, solve for a => verify all x.
        for (unsigned int x = 1; x < sz; x++) {
            unsigned int xd = gf_pow(ctx, x, d);
            if (xd == 0) continue; // Can't invert.
            unsigned int fx = LUT[x];
            unsigned int diff = fx ^ b; // GF(2^n) => XOR.
            unsigned int a = 0;
            if (diff != 0) {
                // a = diff * inv(xd) => diff * x^( (sz-1)-d ).
                unsigned int inv_xd = gf_pow(ctx, x, (sz - 1 - d));
                a = gf_mul(ctx, diff, inv_xd);
            }
            found_candidate_a = true;

            // Check for all x.
            bool ok = true;
            for (unsigned int xx = 0; xx < sz; xx++) {
                unsigned int xx_d = gf_pow(ctx, xx, d);
                unsigned int val = b;
                if (a != 0 && xx_d != 0) {
                    unsigned int mul_ = gf_mul(ctx, a, xx_d);
                    val ^= mul_;
                }
                if (val != LUT[xx]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                return true;
            }
            // If not ok, break and try next d.
            break;
        }
        // If we never found x^d != 0 => move on.
        if (!found_candidate_a) {
            continue;
        }
    }
    return false;
}

extern "C" bool
function_is_monomial(function_t fh)
{
    if (!fh) return false;
    FunctionHandle* handle = reinterpret_cast<FunctionHandle*>(fh);
    return is_monomial_impl(*handle->func);
}