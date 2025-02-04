/* Nikolay Stoyanov Kaleyski https://github.com/nskal/tripeq/blob/main/alg1.c */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

typedef unsigned long vbf_tt_entry;

typedef struct {
    size_t vbf_tt_dimension;
    size_t vbf_tt_number_of_entries;
    vbf_tt_entry *vbf_tt_values;
} vbf_tt;

static bool equivalent = false;

typedef struct {
    size_t N;
    size_t tN;
    vbf_tt_entry *t;
    vbf_tt_entry *ol;
} triplicate;

typedef struct {
    size_t N;
    vbf_tt_entry *y;
    vbf_tt_entry *x;
} linear;

static bool is_canonical_triplicate_internal(vbf_tt F, triplicate *T);
static void test_triplicate_linear_equivalence(vbf_tt F, vbf_tt G,
                                               triplicate Ft, triplicate Gt);

static void delete_triplicate_from_memory(triplicate T)
{
    if(T.t)  free(T.t);
    if(T.ol) free(T.ol);
}
static void delete_linear_from_memory(linear L)
{
    if(L.x) free(L.x);
    if(L.y) free(L.y);
}

static void configure(triplicate Ft, triplicate Gt, linear L2,
                      size_t f, size_t g, unsigned char xymc, unsigned char cfg);
static void combine(linear L2, vbf_tt_entry *xgs, unsigned char px);
static size_t generate(vbf_tt F, vbf_tt G,
                       linear L1, linear L2,
                       vbf_tt_entry *fgs, vbf_tt_entry *xgs, unsigned char px);
static bool check(vbf_tt F, vbf_tt G,
                  triplicate Ft, triplicate Gt,
                  linear L1, vbf_tt_entry *fgs, size_t a);
static void guess(vbf_tt F, vbf_tt G, triplicate Ft, triplicate Gt,
                  linear L1, linear L2,
                  vbf_tt_entry *fgs, vbf_tt_entry *xgs,
                  unsigned char px, unsigned char cfg);
static void assignFunc(vbf_tt F, vbf_tt G,
                       triplicate Ft, triplicate Gt,
                       linear L1, linear L2,
                       size_t f, size_t g,
                       vbf_tt_entry *fgs, vbf_tt_entry *xgs,
                       unsigned char xymc, unsigned char px, unsigned char cfg);

static unsigned long prim_poly_table[] = {
  /* index=0 => unused, index=dim => known primitive polynomial bits */
  0UL,
  3UL,      /* dim=1 => x + 1 => 11b=>3 */
  7UL,      /* dim=2 => x^2 + x +1 =>111b=>7 */
  13UL,     /* dim=3 => x^3 + x +1 =>1101b=>13 */
  19UL,     /* dim=4 => x^4 + x +1 =>10011b=>19 */
  37UL,     /* dim=5 => x^5 + x^2 +1 =>100101b=>37 */
  67UL,     /* dim=6 => x^6 + x +1 =>1000011b=>67 */
  131UL,    /* dim=7 => x^7 + x +1 =>10000011b=>131 */
  285UL,    /* dim=8 => x^8 + x^4 + x^3 + x +1 =>100011101b=>285 */
  529UL,    /* dim=9 =>  x^9 + x^4 + 1 => 529 */
  1033UL,   /* dim=10 => x^10 + x^3 + 1 => 1033 */
  2053UL,   /* dim=11 => x^11 + x^2 + 1 => 2053 */
  4179UL,   /* dim=12 => x^12 + x^6 + x^4 + x + 1 => 4179 */
  8219UL,   /* dim=13 => x^13 + x^4 + x^3 + x + 1 => 8219 */
  17475UL,  /* dim=14 => (one valid choice) => 17475 */
  32771UL,  /* dim=15 => x^15 + x + 1 => 32771   */
  69643UL,  /* dim=16 => x^16 + x^12 + x^3 + x + 1 => 69643 */
  131081UL, /* dim=17 => x^17 + x^3 + 1 => 131081 */
  262273UL, /* dim=18 => x^18 + x^7 + 1 => 262273 */
  524389UL, /* dim=19 => x^19 + x^6 + x^5 + x^2 + 1 => 524389 */
  1048585UL /* dim=20 => x^20 + x^3 + 1 => 1048585 */
};

static unsigned long vbf_tt_get_primitive_polynomial(size_t dimension)
{
    if(dimension<1 || dimension>20) return 0UL;
    return prim_poly_table[dimension];
}

static unsigned long vbf_tt_ff_multiply(unsigned long a, unsigned long b,
                                        unsigned long pp, size_t dimension)
{
    unsigned long product=0UL;
    for(size_t i=0; i< dimension; i++){
        if(b & 1UL){
            product ^= a;
        }
        b >>= 1UL;
        unsigned long carry = (a & (1UL<<(dimension-1))) ? 1UL : 0UL;
        a <<=1UL;
        if(carry) a ^= pp;
    }
    unsigned long mask = ((unsigned long)1UL << dimension) -1UL;
    return product & mask;
}

static const unsigned long betas[] = {
  /* For dimension=4 =>6, 6=>14, 8=>214, 10=>42,12=>3363,14=>16363,16=>44234,...*/
  6UL, 14UL, 214UL, 42UL, 3363UL, 16363UL, 44234UL, 245434UL, 476308UL
};

static bool is_canonical_triplicate_internal(vbf_tt F, triplicate *T)
{
    printf("[DEBUG] is_canonical_triplicate_internal: dimension=%zu, #entries=%zu\n",
           F.vbf_tt_dimension, F.vbf_tt_number_of_entries);

    if(F.vbf_tt_dimension <4 || F.vbf_tt_dimension>20 ||
       (F.vbf_tt_dimension%2)!=0)
    {
        fprintf(stderr,"error: dimension must be even in [4..20], got=%zu\n",
                F.vbf_tt_dimension);
        return false;
    }

    if(F.vbf_tt_values[0] !=0){
        fprintf(stderr,"error: Not canonical triplicate. F(0)=%lu !=0\n",
                (unsigned long)F.vbf_tt_values[0]);
        return false;
    }

    T->N  = F.vbf_tt_number_of_entries;
    T->tN = (F.vbf_tt_number_of_entries -1)/3;
    T->t  = (vbf_tt_entry*) calloc(T->tN*4, sizeof(vbf_tt_entry));
    T->ol = (vbf_tt_entry*) calloc(T->N,     sizeof(vbf_tt_entry));

    if(!T->t || !T->ol){
        fprintf(stderr,"[DEBUG] mem error in is_canonical_triplicate.\n");
        free(T->t); free(T->ol);
        return false;
    }

    size_t idx = (F.vbf_tt_dimension -4)/2;
    if(idx >= (sizeof(betas)/sizeof(betas[0]))){
        fprintf(stderr,"[DEBUG] dimension out-of-range for snippet betas: %zu\n",
                F.vbf_tt_dimension);
        free(T->t); free(T->ol);
        return false;
    }
    unsigned long beta = betas[idx];
    printf("[DEBUG] snippetBeta=%lu for dimension=%zu (index=%zu)\n", beta, F.vbf_tt_dimension, idx);

    unsigned long pp = vbf_tt_get_primitive_polynomial(F.vbf_tt_dimension);
    printf("[DEBUG] prim_poly=0x%lX for dimension=%zu\n", pp, F.vbf_tt_dimension);

    unsigned char *c = (unsigned char*) malloc(T->N);
    memset(c, 1, T->N);
    c[0] =0;

    size_t j=0;
    for(unsigned long i=1; i< F.vbf_tt_number_of_entries; i++){
        if(c[i]!=0){
            unsigned long Fi = F.vbf_tt_values[i];
            if(Fi==0){
                fprintf(stderr,"error: too many map->0. i=%lu\n", (unsigned long)i);
                free(c);
                return false;
            }
            if(T->ol[Fi]!=0){
                fprintf(stderr,"error: same output used => i=%lu => F(i)=%lu\n",
                        i, Fi);
                free(c);
                return false;
            }
            T->ol[Fi] = j+1;
            T->t[0*T->tN + j] = Fi;
            T->t[1*T->tN + j] = i;
            c[i] =0;

            /* multiply i*beta mod pp => k */
            unsigned long k = vbf_tt_ff_multiply(i, beta, pp, F.vbf_tt_dimension);
            if(F.vbf_tt_values[k] != Fi || F.vbf_tt_values[k ^ i]!= Fi){
                fprintf(stderr,
                    "error: Not canonical triplicate. triple not found.\n"
                    "  [debug] i=%lu => F(i)=%lu, k=%lu => F(k)=%lu, F(k^i)=%lu\n",
                    i, Fi, k, (unsigned long)F.vbf_tt_values[k],
                    (unsigned long)F.vbf_tt_values[k ^ i]);
                free(c);
                return false;
            }
            T->t[2*T->tN + j] = k;
            c[k]=0;
            T->t[3*T->tN + j] = (k ^ i);
            c[k ^ i]=0;
            j++;
        }
    }
    free(c);
    printf("[DEBUG] is_canonical_triplicate => success with j=%zu.\n", j);
    return true;
}

#ifdef __cplusplus
extern "C" {
#endif

bool check_is_canonical_triplicate(vbf_tt *F)
{
    printf("[DEBUG] check_is_canonical_triplicate: dimension=%zu\n",
           F->vbf_tt_dimension);

    printf("[DEBUG] Full TT (length=%zu):", F->vbf_tt_number_of_entries);
    for (size_t i = 0; i < F->vbf_tt_number_of_entries; i++) {
        printf(" %lu", (unsigned long)F->vbf_tt_values[i]);
    }
    printf("\n");

    triplicate T; 
    T.t=NULL; 
    T.ol=NULL;

    bool ok = is_canonical_triplicate_internal(*F, &T);
    if(T.t || T.ol){
        delete_triplicate_from_memory(T);
    }
    return ok;
}

#ifdef __cplusplus
}
#endif

static void print_linear(linear L)
{
    printf("\n[DEBUG] print_linear => dimension N=%zu\n  y=", L.N);
    for(size_t i=0; i< L.N; i++){
        printf(" %lu",(unsigned long)L.y[i]);
    }
    printf("\n");

    printf("  x=");
    for(size_t i=0; i< L.N; i++){
        printf(" %lu",(unsigned long)L.x[i]);
    }
    printf("\n");
}


static void test_triplicate_linear_equivalence(vbf_tt F, vbf_tt G,
                                               triplicate Ft, triplicate Gt)
{
    printf("[DEBUG] test_triplicate_linear_equivalence: dim=%zu\n",
           F.vbf_tt_dimension);
    equivalent = false;

    linear L1, L2;
    L1.N = F.vbf_tt_number_of_entries;
    L2.N = F.vbf_tt_number_of_entries;

    L1.x = (vbf_tt_entry*) calloc(L1.N,sizeof(vbf_tt_entry));
    L1.y = (vbf_tt_entry*) calloc(L1.N,sizeof(vbf_tt_entry));
    L2.x = (vbf_tt_entry*) calloc(L2.N,sizeof(vbf_tt_entry));
    L2.y = (vbf_tt_entry*) calloc(L2.N,sizeof(vbf_tt_entry));

    vbf_tt_entry *fgs = (vbf_tt_entry*) calloc(2*F.vbf_tt_number_of_entries, sizeof(vbf_tt_entry));
    vbf_tt_entry *xgs = (vbf_tt_entry*) calloc(F.vbf_tt_number_of_entries,   sizeof(vbf_tt_entry));

    size_t f=0, g=0;
    unsigned char xymc=0, px=0;

    while(g < Gt.tN){
        L1.y[ Ft.t[f]] = Gt.t[g];
        L1.x[ Gt.t[g]] = Ft.t[f];

        fgs[0] = Ft.t[f];
        fgs[F.vbf_tt_number_of_entries] =1; /* mark guess 0 as configured */
        xgs[0] = Gt.t[1*Gt.tN + g];
        xgs[1] = Gt.t[2*Gt.tN + g];
        xgs[2] = Gt.t[3*Gt.tN + g];

        memset(L2.x, 0, L2.N*sizeof(vbf_tt_entry));
        memset(L2.y, 0, L2.N*sizeof(vbf_tt_entry));

        assignFunc(F, G, Ft, Gt, L1, L2, f, g, fgs, xgs, xymc, px, 1);
        if(equivalent) break;
        assignFunc(F, G, Ft, Gt, L1, L2, f, g, fgs, xgs, xymc, px, 2);
        if(equivalent) break;

        /* revert: */
        L1.y[ Ft.t[f]] =0;
        L1.x[ Gt.t[g]] =0;
        g++;
    }
    if(!equivalent){
        printf("False\n");
    }

    free(L1.x); free(L1.y);
    free(L2.x); free(L2.y);
    free(fgs);
    free(xgs);
}

static void assignFunc(vbf_tt F, vbf_tt G,
                       triplicate Ft, triplicate Gt,
                       linear L1, linear L2,
                       size_t f, size_t g,
                       vbf_tt_entry *fgs, vbf_tt_entry *xgs,
                       unsigned char xymc, unsigned char px, unsigned char cfg)
{
    while(xymc<3){
        configure(Ft, Gt, L2, f, g, xymc, cfg);

        linear l1, l2_local;
        l1.N = F.vbf_tt_number_of_entries;
        l2_local.N = F.vbf_tt_number_of_entries;
        l1.x = (vbf_tt_entry*) malloc(l1.N*sizeof(vbf_tt_entry));
        l1.y = (vbf_tt_entry*) malloc(l1.N*sizeof(vbf_tt_entry));
        l2_local.x = (vbf_tt_entry*) malloc(l2_local.N*sizeof(vbf_tt_entry));
        l2_local.y = (vbf_tt_entry*) malloc(l2_local.N*sizeof(vbf_tt_entry));

        vbf_tt_entry *fgss = (vbf_tt_entry*) malloc(2*F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));

        for(size_t i=0; i< l1.N; i++){
            l1.x[i] = L1.x[i];
            l1.y[i] = L1.y[i];
            l2_local.x[i] = L2.x[i];
            l2_local.y[i] = L2.y[i];
            fgss[i] = fgs[i];
            fgss[F.vbf_tt_number_of_entries + i] = fgs[F.vbf_tt_number_of_entries + i];
        }

        combine(l2_local, xgs, px);
        size_t a = generate(F, G, l1, l2_local, fgss, xgs, px);
        if(a!=0){
            if(check(F, G, Ft, Gt, l1, fgss, a)){
                guess(F, G, Ft, Gt, l1, l2_local, fgss, xgs, px+1, cfg);
                if(equivalent){
                    delete_linear_from_memory(l1);
                    delete_linear_from_memory(l2_local);
                    free(fgss);
                    return;
                }
            }
        }
        delete_linear_from_memory(l1);
        delete_linear_from_memory(l2_local);
        free(fgss);

        xymc++;
    }
}

/*********************************************************************************
 * configure(...)
 *********************************************************************************/
static void configure(triplicate Ft, triplicate Gt, linear L2,
                      size_t f, size_t g, unsigned char xymc, unsigned char cfg)
{
    if(cfg==1){
        switch(xymc){
        case 0:
            L2.y[ Gt.t[1*Gt.tN + g]] = Ft.t[1*Ft.tN + f];
            L2.x[ Ft.t[1*Ft.tN + f]] = Gt.t[1*Gt.tN + g];
            L2.y[ Gt.t[2*Gt.tN + g]] = Ft.t[2*Ft.tN + f];
            L2.x[ Ft.t[2*Ft.tN + f]] = Gt.t[2*Gt.tN + g];
            L2.y[ Gt.t[3*Gt.tN + g]] = Ft.t[3*Ft.tN + f];
            L2.x[ Ft.t[3*Ft.tN + f]] = Gt.t[3*Gt.tN + g];
            break;
        case 1:
            L2.y[ Gt.t[1*Gt.tN + g]] = Ft.t[2*Ft.tN + f];
            L2.x[ Ft.t[2*Ft.tN + f]] = Gt.t[1*Gt.tN + g];
            L2.y[ Gt.t[2*Gt.tN + g]] = Ft.t[3*Ft.tN + f];
            L2.x[ Ft.t[3*Ft.tN + f]] = Gt.t[2*Gt.tN + g];
            L2.y[ Gt.t[3*Gt.tN + g]] = Ft.t[1*Ft.tN + f];
            L2.x[ Ft.t[1*Ft.tN + f]] = Gt.t[3*Gt.tN + g];
            break;
        case 2:
            L2.y[ Gt.t[1*Gt.tN + g]] = Ft.t[3*Ft.tN + f];
            L2.x[ Ft.t[3*Ft.tN + f]] = Gt.t[1*Gt.tN + g];
            L2.y[ Gt.t[2*Gt.tN + g]] = Ft.t[1*Ft.tN + f];
            L2.x[ Ft.t[1*Ft.tN + f]] = Gt.t[2*Gt.tN + g];
            L2.y[ Gt.t[3*Gt.tN + g]] = Ft.t[2*Ft.tN + f];
            L2.x[ Ft.t[2*Ft.tN + f]] = Gt.t[3*Gt.tN + g];
            break;
        default:
            return;
        }
    } else {
        switch(xymc){
        case 0:
            L2.y[ Gt.t[1*Gt.tN + g]] = Ft.t[2*Ft.tN + f];
            L2.x[ Ft.t[2*Ft.tN + f]] = Gt.t[1*Gt.tN + g];
            L2.y[ Gt.t[2*Gt.tN + g]] = Ft.t[1*Ft.tN + f];
            L2.x[ Ft.t[1*Ft.tN + f]] = Gt.t[2*Gt.tN + g];
            L2.y[ Gt.t[3*Gt.tN + g]] = Ft.t[3*Ft.tN + f];
            L2.x[ Ft.t[3*Ft.tN + f]] = Gt.t[3*Gt.tN + g];
            break;
        case 1:
            L2.y[ Gt.t[1*Gt.tN + g]] = Ft.t[3*Ft.tN + f];
            L2.x[ Ft.t[3*Ft.tN + f]] = Gt.t[1*Gt.tN + g];
            L2.y[ Gt.t[2*Gt.tN + g]] = Ft.t[2*Ft.tN + f];
            L2.x[ Ft.t[2*Ft.tN + f]] = Gt.t[2*Gt.tN + g];
            L2.y[ Gt.t[3*Gt.tN + g]] = Ft.t[1*Ft.tN + f];
            L2.x[ Ft.t[1*Ft.tN + f]] = Gt.t[3*Gt.tN + g];
            break;
        case 2:
            L2.y[ Gt.t[1*Gt.tN + g]] = Ft.t[1*Ft.tN + f];
            L2.x[ Ft.t[1*Ft.tN + f]] = Gt.t[1*Gt.tN + g];
            L2.y[ Gt.t[2*Gt.tN + g]] = Ft.t[3*Ft.tN + f];
            L2.x[ Ft.t[3*Ft.tN + f]] = Gt.t[2*Gt.tN + g];
            L2.y[ Gt.t[3*Gt.tN + g]] = Ft.t[2*Ft.tN + f];
            L2.x[ Ft.t[2*Ft.tN + f]] = Gt.t[3*Gt.tN + g];
            break;
        default:
            return;
        }
    }
}

/*********************************************************************************
 * combine(...)
 *********************************************************************************/
static void combine(linear L2, vbf_tt_entry *xgs, unsigned char px)
{
    size_t a = (1<<(2*px)) -1;
    size_t b = a +3;
}

static size_t generate(vbf_tt F, vbf_tt G,
                       linear L1, linear L2,
                       vbf_tt_entry *fgs, vbf_tt_entry *xgs,
                       unsigned char px)
{
    size_t a = (1<<(2*px)) +2;
    size_t b = (1<<(2*(px+1))) -1;
    size_t n=0;
    while(fgs[n]!=0) n++;
    size_t j=n;

    for(size_t i=a; i<b; i+=3){
        vbf_tt_entry gVal = G.vbf_tt_values[xgs[i]];
        vbf_tt_entry fVal = F.vbf_tt_values[L2.y[xgs[i]]];
        if((fVal==0 && gVal!=0)||(gVal==0 && fVal!=0)) return 0;
        if(L1.x[gVal]!=0 && L1.x[gVal]!=fVal) return 0;
        if(L1.y[fVal]!=0 && L1.y[fVal]!=gVal) return 0;
        if(L1.y[fVal]!=0){
            for(size_t k2=0; k2<n; k2++){
                if(fgs[k2]==fVal){
                    fgs[F.vbf_tt_number_of_entries + k2]=1;
                    break;
                }
            }
        } else {
            fgs[n]= fVal;
            fgs[F.vbf_tt_number_of_entries + n]=1;
            n++;
            L1.y[fVal]= gVal;
            L1.x[gVal]= fVal;
        }
    }
    return j;
}

static bool check(vbf_tt F, vbf_tt G,
                  triplicate Ft, triplicate Gt,
                  linear L1, vbf_tt_entry *fgs, size_t a)
{
    size_t b=0;
    while(fgs[b]!=0) b++;
    size_t n=b;
    size_t k=b;

    for(size_t i=a; i<b; i++){
        for(size_t j=0; j<i; j++){
            vbf_tt_entry fVal= fgs[i]^ fgs[j];
            vbf_tt_entry gVal= L1.y[fgs[i]] ^ L1.y[fgs[j]];
            if((fVal==0 && gVal!=0)||(gVal==0 && fVal!=0)) return false;
            if(L1.x[gVal]!=0 && L1.x[gVal]!=fVal) return false;
            if(L1.y[fVal]!=0 && L1.y[fVal]!=gVal) return false;
            if(L1.y[fVal]==0 && fVal!=0){
                if(Ft.ol[fVal]!=0 && Gt.ol[gVal]!=0){
                    fgs[k]= fVal; k++;
                    L1.y[fVal]= gVal; L1.x[gVal]= fVal;
                }
                else if(Ft.ol[fVal]==0 && Gt.ol[gVal]==0){
                    fgs[k]= fVal;
                    fgs[F.vbf_tt_number_of_entries + k]=1;
                    k++;
                    L1.y[fVal]= gVal; L1.x[gVal]= fVal;
                }
                else return false;
            }
        }
        for(size_t jj=b; jj<n; jj++){
            vbf_tt_entry fVal= fgs[i]^ fgs[jj];
            vbf_tt_entry gVal= L1.y[fgs[i]] ^ L1.y[fgs[jj]];
            if((fVal==0 && gVal!=0)||(gVal==0 && fVal!=0)) return false;
            if(L1.x[gVal]!=0 && L1.x[gVal]!= fVal) return false;
            if(L1.y[fVal]!=0 && L1.y[fVal]!= gVal) return false;
            if(L1.y[fVal]==0 && fVal!=0){
                if(Ft.ol[fVal]!=0 && Gt.ol[gVal]!=0){
                    fgs[k]= fVal; k++;
                    L1.y[fVal]= gVal; L1.x[gVal]= fVal;
                }
                else if(Ft.ol[fVal]==0 && Gt.ol[gVal]==0){
                    fgs[k]= fVal;
                    fgs[F.vbf_tt_number_of_entries + k]=1;
                    k++;
                    L1.y[fVal]= gVal; L1.x[gVal]= fVal;
                }
                else return false;
            }
        }
        n=k;
    }
    return true;
}

static void guess(vbf_tt F, vbf_tt G,
                  triplicate Ft, triplicate Gt,
                  linear L1, linear L2,
                  vbf_tt_entry *fgs, vbf_tt_entry *xgs,
                  unsigned char px, unsigned char cfg)
{
    size_t pf=0;
    size_t i, n;
    n = (1<<(2*px)) -1;

    for(i=0; i< (F.vbf_tt_number_of_entries -1); i++){
        if(fgs[F.vbf_tt_number_of_entries + i]==0){
            pf=i; 
            break;
        }
    }
    if(i==(F.vbf_tt_number_of_entries -1)){
        equivalent=true;
        print_linear(L1);
        print_linear(L2);
        return;
    }

    if(fgs[pf]!=0){
        vbf_tt_entry fVal = Ft.ol[ fgs[pf]] -1;
        vbf_tt_entry gVal = Gt.ol[ L1.y[fgs[pf]]] -1;

        linear l2_local;
        l2_local.N = F.vbf_tt_number_of_entries;
        l2_local.x= (vbf_tt_entry*) malloc(l2_local.N*sizeof(vbf_tt_entry));
        l2_local.y= (vbf_tt_entry*) malloc(l2_local.N*sizeof(vbf_tt_entry));
        vbf_tt_entry *fgss= (vbf_tt_entry*) malloc(2*F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));

        for(i=0; i< l2_local.N; i++){
            l2_local.x[i] = L2.x[i];
            l2_local.y[i] = L2.y[i];
            fgss[i] = fgs[i];
            fgss[F.vbf_tt_number_of_entries + i] = fgs[F.vbf_tt_number_of_entries + i];
        }
        fgss[F.vbf_tt_number_of_entries + pf] =1;
        xgs[n]   = Gt.t[1*Gt.tN + gVal];
        xgs[n+1] = Gt.t[2*Gt.tN + gVal];
        xgs[n+2] = Gt.t[3*Gt.tN + gVal];

        assignFunc(F, G, Ft, Gt, L1, l2_local, fVal, gVal, fgss, xgs, 0, px, cfg);
        delete_linear_from_memory(l2_local);
        free(fgss);
        if(equivalent) return;
    } else {
        vbf_tt_entry fVal=0, gVal=0;
        while(L1.y[ Ft.t[fVal]]!=0 && fVal< Ft.tN) fVal++;
        while(L1.x[ Gt.t[gVal]]!=0 && gVal< Gt.tN) gVal++;
        while(gVal< Gt.tN){
            linear l1;
            l1.N= F.vbf_tt_number_of_entries;
            l1.x= (vbf_tt_entry*) malloc(l1.N*sizeof(vbf_tt_entry));
            l1.y= (vbf_tt_entry*) malloc(l1.N*sizeof(vbf_tt_entry));
            vbf_tt_entry *fgss= (vbf_tt_entry*) malloc(2*F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));

            for(i=0; i< l1.N; i++){
                l1.x[i] = L1.x[i];
                l1.y[i] = L1.y[i];
                fgss[i] = fgs[i];
                fgss[F.vbf_tt_number_of_entries + i] = fgs[F.vbf_tt_number_of_entries + i];
            }
            l1.y[ Ft.t[fVal]] = Gt.t[gVal];
            l1.x[ Gt.t[gVal]] = Ft.t[fVal];
            fgss[pf] = Ft.t[fVal];

            if(check(F,G, Ft,Gt, l1, fgss, pf)){
                fgss[F.vbf_tt_number_of_entries + pf] =1;
                linear l2_local;
                l2_local.N = F.vbf_tt_number_of_entries;
                l2_local.x = (vbf_tt_entry*) malloc(l2_local.N*sizeof(vbf_tt_entry));
                l2_local.y = (vbf_tt_entry*) malloc(l2_local.N*sizeof(vbf_tt_entry));
                for(size_t z=0; z< l2_local.N; z++){
                    l2_local.x[z] = L2.x[z];
                    l2_local.y[z] = L2.y[z];
                }
                xgs[n]   = Gt.t[1*Gt.tN + gVal];
                xgs[n+1] = Gt.t[2*Gt.tN + gVal];
                xgs[n+2] = Gt.t[3*Gt.tN + gVal];

                assignFunc(F,G, Ft,Gt, l1, l2_local, fVal, gVal, fgss, xgs, 0, px, cfg);
                delete_linear_from_memory(l2_local);
            }
            delete_linear_from_memory(l1);
            free(fgss);
            if(equivalent) return;
            gVal++;
            while(L1.x[ Gt.t[gVal]]!=0 && gVal<Gt.tN) gVal++;
        }
    }
}

#ifdef __cplusplus
extern "C" {
#endif

bool run_alg1_equivalence_test(size_t dimF, const unsigned long *ttF,
                               size_t dimG, const unsigned long *ttG)
{
    printf("[DEBUG] run_alg1_equivalence_test: dimF=%zu, dimG=%zu\n", dimF, dimG);

    if(dimF != dimG){
        fprintf(stderr,"[DEBUG] dimension mismatch => false.\n");
        return false;
    }

    size_t nF = (size_t)1 << dimF;
    size_t nG = (size_t)1 << dimG;

    vbf_tt F;
    F.vbf_tt_dimension = dimF;
    F.vbf_tt_number_of_entries = nF;
    F.vbf_tt_values = (vbf_tt_entry*) malloc(nF*sizeof(vbf_tt_entry));
    if(!F.vbf_tt_values){
        fprintf(stderr,"Memory error F.\n");
        return false;
    }
    for(size_t i=0; i<nF; i++){
        F.vbf_tt_values[i] = ttF[i];
    }

    printf("[DEBUG] TT of F (dim=%zu, length=%zu):", F.vbf_tt_dimension, nF);
    for (size_t i = 0; i < nF; i++) {
        printf(" %lu", (unsigned long)F.vbf_tt_values[i]);
    }
    printf("\n");

    vbf_tt G;
    G.vbf_tt_dimension = dimG;
    G.vbf_tt_number_of_entries = nG;
    G.vbf_tt_values = (vbf_tt_entry*) malloc(nG*sizeof(vbf_tt_entry));
    if(!G.vbf_tt_values){
        free(F.vbf_tt_values);
        fprintf(stderr,"Memory error G.\n");
        return false;
    }
    for(size_t i=0; i<nG; i++){
        G.vbf_tt_values[i] = ttG[i];
    }

    printf("[DEBUG] TT of G (dim=%zu, length=%zu):", G.vbf_tt_dimension, nG);
    for (size_t i = 0; i < nG; i++) {
        printf(" %lu", (unsigned long)G.vbf_tt_values[i]);
    }
    printf("\n");
    
    triplicate Ft; Ft.t=NULL; Ft.ol=NULL;
    triplicate Gt; Gt.t=NULL; Gt.ol=NULL;
    equivalent = false;

    bool okF = is_canonical_triplicate_internal(F, &Ft);
    bool okG = is_canonical_triplicate_internal(G, &Gt);

    if(!okF || !okG){
        fprintf(stderr,"error: Function is not canonical triplicate. Triple not found.\n");
        delete_triplicate_from_memory(Ft);
        delete_triplicate_from_memory(Gt);
        free(F.vbf_tt_values);
        free(G.vbf_tt_values);
        return false;
    }

    test_triplicate_linear_equivalence(F, G, Ft, Gt);
    bool ret = equivalent;

    delete_triplicate_from_memory(Ft);
    delete_triplicate_from_memory(Gt);
    free(F.vbf_tt_values);
    free(G.vbf_tt_values);
    return ret;
}

#ifdef __cplusplus
}
#endif