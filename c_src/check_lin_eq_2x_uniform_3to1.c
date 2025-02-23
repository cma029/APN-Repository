/*****************************************************************************/
/*  check_lin_eq_2x_uniform_3to1.c                                           */
/*                                                                           */
/*  Adapted from the nskal/tripeq repository at:                             */
/*    https://github.com/nskal/tripeq/tree/main                              */
/*  Contributors include: Ivana Ivkovic and Nikolay Stoyanov Kaleyski.       */
/*                                                                           */
/*  This file extracts the relevant logic from alg1.c to check linear        */
/*  equivalence for canonical 3-to-1 (triplicate) functions modified         */
/*  for in memory-based usage instead of reading from files.                 */
/*                                                                           */
/*  The main function check_lin_eq_2x_uniform_3to1(...) returns 'True'       */
/*  if two functions (same dimension) are linearly equivalent and both are   */
/*  canonical 3-to-1. Otherwise it returns 'False'.                          */
/*                                                                           */
/*****************************************************************************/

#include "check_lin_eq_2x_uniform_3to1.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>


/* -----------------------------------------------------------------------
   Minimal Finite-Field Routines ( extracted from vbf.c / vbf.h ).
   ----------------------------------------------------------------------- */

/* Library of primitive polynomials */
static unsigned long get_primitive_polynomial(size_t dimension) {
    static unsigned long pps[] = {
        7UL,       11UL,       19UL,       37UL,       91UL,
        131UL,     285UL,      529UL,      1135UL,     2053UL,
        4331UL,    8219UL,     16553UL,    32821UL,    65581UL,
        131081UL,  267267UL,   524327UL,   1050355UL,  2097253UL,
        4202337UL, 8388641UL,  16901801UL, 33554757UL, 67126739UL,
        134223533UL, 268443877UL, 536870917UL, 1073948847UL, 2147483657UL,
        4295000729UL, 8589950281UL, 17179974135UL, 34359741605UL, 68733788515UL,
        137438953535UL, 274877925159UL, 549755854565UL, 1099522486571UL, 2199023255561UL,
        4399239010919UL, 8796093022297UL, 17592203542555UL, 35184373323841UL, 70368755859457UL,
        140737488355361UL, 281475018792329UL, 562949953422687UL, 1125900847118165UL
    };

    /* Code only realistically uses 4 <= dimension <= 20 (even). */
    if(dimension < 2 || dimension > 50) {
        /* Fallback or error: returns 0 if out of range. */
        return 0UL;
    }
    return pps[dimension - 2];
}

/*
 * Finite field multiplication: multiply a, b in GF(2^dimension),
 * with the primitive polynomial 'pp' (bitmask form).
 * Source from vbf_tt_ff_multiply in vbf.c
 */
static unsigned long ff_multiply(unsigned long a, unsigned long b,
                                 unsigned long pp, size_t dimension)
{
    unsigned long result = 0UL;
    /* The bit at position (dimension-1) is the cutoff for reduction. */
    unsigned long cutoff = 1UL << (dimension - 1);

    while(a && b) {
        if (b & 1UL) { /* if b is odd, add a to the total */
            result ^= a;
        }
        b >>= 1;
        if (a & cutoff) {
            a = (a << 1) ^ pp; /* reduce */
        } else {
            a <<= 1;
        }
    }
    return result;
}

/*
 * pre-generated betas for the triplicate functions from dimension 4 to dimension 20. 
 * alg1.c uses a small pre-generated array of betas for n in [4..20] (provided n is even, >= 4).
 */
static unsigned long get_beta(size_t n) {
    if(n < 4 || n > 20 || (n % 2)) {
        fprintf (stderr, "error: Beta is a primitive element of F2^4 in even dimension n: 4 <= n <= 20.\n");
        return 0UL;
    }
    /* Beta array (n=4..20 in steps of 2). */
    static unsigned long betas[] = {
       6UL,       /* for n=4  */
       14UL,      /* for n=6  */
       214UL,     /* for n=8  */
       42UL,      /* for n=10 */
       3363UL,    /* for n=12 */
       16363UL,   /* for n=14 */
       44234UL,   /* for n=16 */
       245434UL,  /* for n=18 */
       476308UL   /* for n=20 */
    };
    size_t index = (n - 4)/2;
    return betas[index];
}

/* -----------------------------------------------------------------------
   Structures from alg1.c: triplicate & linear.
   ----------------------------------------------------------------------- */
typedef struct {
   size_t N;          /* number of elements = 2^n */
   size_t tN;         /* number of triples => (2^n - 1)/3 */
   vbf_tt_entry *t;   /* the triplicate table: 4 blocks of size tN / output & 3 preimages */
   vbf_tt_entry *ol;  /* output lookup: for each possible (nonzero) output, store index+1 */
} triplicate;

typedef struct {
   size_t N;          /* number of elements = 2^n */
   vbf_tt_entry *y;   /* x -> y  values: mapping for the linear guess */
   vbf_tt_entry *x;   /* y -> x  pre-images: inverse mapping for the linear guess */
} linear;

/* Global (static) used by the search to indicate success. */
static bool g_equivalent = false;

/* -----------------------------------------------------------------------
   Utility: free triplicate & linear from memory.
   ----------------------------------------------------------------------- */
static void delete_triplicate_from_memory(triplicate T) {
   free(T.t);
   free(T.ol);
}

static void delete_linear_from_memory(linear L) {
   free(L.y);
   free(L.x);
}

/* -----------------------------------------------------------------------
   Check if a vbf_tt is a canonical triplicate (3-to-1) function.
   ----------------------------------------------------------------------- */
static bool is_canonical_triplicate_internal(const vbf_tt *F, triplicate *T) {
   /* Function: check if triplicate and return triplicate representation. */
   if (F->vbf_tt_dimension < 4 || F->vbf_tt_dimension > 20 || (F->vbf_tt_dimension % 2)) {
      fprintf(stderr, "error: Triplicate requires even n in [4..20]. Max n=20 implemented.\n");
      return false;
   }
   /* Must have F(0) = 0. */
   if (F->vbf_tt_values[0] != 0UL) {
   /* 
    * Commented out to reduce verbose printout.
    * fprintf(stderr, "error: F(0) != 0 => Function is not canonical triplicate.\n");
    */
      return false;
   }

   T->N  = F->vbf_tt_number_of_entries;
   T->tN = (F->vbf_tt_number_of_entries - 1)/3;
   T->t  = (vbf_tt_entry *) calloc(T->tN * 4, sizeof(vbf_tt_entry));
   T->ol = (vbf_tt_entry *) calloc(T->N,     sizeof(vbf_tt_entry));

   unsigned long beta_val = get_beta(F->vbf_tt_dimension);
   if(!beta_val) {
      fprintf(stderr, "error: Beta invalid for dimension %lu.\n", (unsigned long)F->vbf_tt_dimension);
      return false;
   }

   /* We allocate a small array c[] to mark visited elements. */
   unsigned char *c = (unsigned char *) malloc(T->N * sizeof(unsigned char));
   memset(c, 1, T->N * sizeof(unsigned char));

   c[0] = 0;  /* We do not re-check 0. */
   size_t j = 0;

   for(size_t i = 1; i < F->vbf_tt_number_of_entries; i++) {
      if (c[i] != 0) {
         if(F->vbf_tt_values[i] == 0) {
            fprintf(stderr, "error: Not a canonical triplicate. Too many elements map to 0.\n");
            free(c);
            return false;
         }
         if(T->ol[F->vbf_tt_values[i]] != 0) {
            fprintf(stderr, "error: Not a canonical triplicate. Too many elements map to same value.\n");
            free(c);
            return false;
         }
         T->ol[F->vbf_tt_values[i]] = j + 1;
         T->t[(0 * T->tN) + j] = F->vbf_tt_values[i]; /* the output */
         T->t[(1 * T->tN) + j] = i;                   /* 1st preimage */

         c[i] = 0;

         /* multiply i by beta in GF(2^n): k = i * beta */
         unsigned long pp = get_primitive_polynomial(F->vbf_tt_dimension);
         unsigned long k  = ff_multiply(i, beta_val, pp, F->vbf_tt_dimension);

         if( (F->vbf_tt_values[k] != F->vbf_tt_values[i]) ||
             (F->vbf_tt_values[k ^ i] != F->vbf_tt_values[i]) ) {
            fprintf(stderr, "error: Function is not canonical triplicate. Triple not found.\n");
            free(c);
            return false;
         }
         T->t[(2 * T->tN) + j] = k;
         c[k] = 0;
         T->t[(3 * T->tN) + j] = (k ^ i);
         c[k ^ i] = 0;

         j += 1;
      }
   }

   free(c);
   return true;
}

/* 
 * Local prototypes: from alg1.c, all the statics to do the equivalence search.
 * They rely on a global 'g_equivalent' to store success.
 */
static bool check( const vbf_tt F, const vbf_tt G,
                   const triplicate Ft, const triplicate Gt,
                   linear L1, vbf_tt_entry *fgs, size_t a );

static void guess(const vbf_tt F, const vbf_tt G,
                  const triplicate Ft, const triplicate Gt,
                  linear L1, linear L2,
                  vbf_tt_entry *fgs, vbf_tt_entry *xgs,
                  unsigned char px, unsigned char cfg);

static void assignF( const vbf_tt F, const vbf_tt G,
                     const triplicate Ft, const triplicate Gt,
                     linear L1, linear L2,
                     size_t f, size_t g,
                     vbf_tt_entry *fgs, vbf_tt_entry *xgs,
                     unsigned char xymc, unsigned char px, unsigned char cfg);

/* -----------------------------------------------------------------------
   Definitions from alg1.c: check, guess, assign, etc.
   ----------------------------------------------------------------------- */

/* check(...) */
static bool check(const vbf_tt F, const vbf_tt G, const triplicate Ft, const triplicate Gt,
                  linear L1, vbf_tt_entry *fgs, size_t a) {

   size_t b = 0, i, j, k, n;
   vbf_tt_entry f, gv;

   while(fgs[b] != 0) b++;
   n = b;
   k = b;

   for(i = a; i < b; i++){
      for(j = 0; j < i; j++){
         f  = fgs[i] ^ fgs[j];
         gv = L1.y[fgs[i]] ^ L1.y[fgs[j]];
         if ((f==0 && gv!=0) || (gv==0 && f!=0)) return false;
         if (L1.x[gv]!=0 && L1.x[gv]!=f) return false;
         if (L1.y[f]!=0 && L1.y[f]!=gv) return false;
         if (L1.y[f]==0 && f!=0){
            if(Ft.ol[f]!=0 && Gt.ol[gv]!=0){ /* if both values are present as triplet outputs. */
               fgs[k] = f;
               k += 1;
               L1.y[f] = gv;
               L1.x[gv] = f;

            } else if (Ft.ol[f]==0 && Gt.ol[gv]==0){ /* if both values are not present in triplet outputs */
               fgs[k] = f;
               fgs[F.vbf_tt_number_of_entries + k] = 1; /* we will not derive any info from there, therefore it is ok to set them to assigned */
               k += 1;
               L1.y[f] = gv;
               L1.x[gv] = f;

            } else return false; /* contradiction */
         }
      }
      for(j = b; j < n; j++){
         f  = fgs[i] ^ fgs[j];
         gv = L1.y[fgs[i]] ^ L1.y[fgs[j]];
         if ((f==0 && gv!=0) || (gv==0 && f!=0)) return false;
         if (L1.x[gv]!=0 && L1.x[gv]!=f) return false;
         if (L1.y[f]!=0 && L1.y[f]!=gv) return false;
         if (L1.y[f]==0 && f!=0){
            if(Ft.ol[f]!=0 && Gt.ol[gv]!=0){
               fgs[k] = f;
               k += 1;
               L1.y[f] = gv;
               L1.x[gv] = f;

            } else if (Ft.ol[f]==0 && Gt.ol[gv]==0){
               fgs[k] = f;
               fgs[F.vbf_tt_number_of_entries + k] = 1;
               k += 1;
               L1.y[f] = gv;
               L1.x[gv] = f;

            } else return false;
         }
      }
      n = k;
   }

   return true;
}

/* guess(...) */
static void guess(const vbf_tt F, const vbf_tt G, const triplicate Ft, const triplicate Gt, linear L1, linear L2,
                  vbf_tt_entry *fgs, vbf_tt_entry *xgs, unsigned char px, unsigned char cfg) {

   size_t i, pf, n;
   vbf_tt_entry f, g;
   vbf_tt_entry *fgss;
   linear l1, l2;

   l1.N = L1.N;
   l2.N = L2.N;
   n = (1<<(2*px)) - 1;

   for(i = 0; i < F.vbf_tt_number_of_entries - 1; i++){
      if(fgs[F.vbf_tt_number_of_entries + i]==0){
         pf = i;
         break;
      }
   }
   if(i == F.vbf_tt_number_of_entries - 1){
      /* or px == (F.vbf_tt_dimension/2)+1 => any one of these conditions means success. */
      g_equivalent = true;
      return;
   }

   if(fgs[pf]!=0){

      f = Ft.ol[fgs[pf]] - 1;
      g = Gt.ol[L1.y[fgs[pf]]] - 1;

      l2.x = (vbf_tt_entry *) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
      l2.y = (vbf_tt_entry *) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
      fgss  = (vbf_tt_entry *) malloc(2*F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));

      for(i=0; i<F.vbf_tt_number_of_entries; i++){
         l2.x[i]    = L2.x[i];
         l2.y[i]    = L2.y[i];
         fgss[i]    = fgs[i];
         fgss[F.vbf_tt_number_of_entries + i] = fgs[F.vbf_tt_number_of_entries + i];
      }
      /* add its L2 values to L2 guesses. */
      fgss[F.vbf_tt_number_of_entries + pf] = 1;
      xgs[n]   = Gt.t[1 * Gt.tN + g];
      xgs[n+1] = Gt.t[2 * Gt.tN + g];
      xgs[n+2] = Gt.t[3 * Gt.tN + g];

      /* and assign L2 configuration: */
      assignF(F, G, Ft, Gt, L1, l2, f, g, fgss, xgs, 0, px, cfg);
      delete_linear_from_memory(l2);
      free(fgss);
      return;
   
   } else {
      /* find free values to pair for L1. */
      f = 0;
      while(L1.y[Ft.t[f]]!=0 && f<Ft.tN) f+=1;
      size_t g_ = 0;
      while(L1.x[Gt.t[g_]]!=0 && g_<Gt.tN) g_+=1;
      while(g_<Gt.tN) {
         /* generate a copy of L1 and fgs not to mess 'em up. */
         l1.x = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
         l1.y = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
         fgss = (vbf_tt_entry*) malloc(2*F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));

         for(i=0; i<F.vbf_tt_number_of_entries; i++){
            l1.x[i] = L1.x[i];
            l1.y[i] = L1.y[i];
            fgss[i] = fgs[i];
            fgss[F.vbf_tt_number_of_entries + i] = fgs[F.vbf_tt_number_of_entries + i];
         }

         /* make a guess; give new assignment to L1. */
         l1.y[Ft.t[f]] = Gt.t[g_];
         l1.x[Gt.t[g_]] = Ft.t[f];
         fgss[pf] = Ft.t[f];

         /* generate its linear combos and check. */
         if(check(F,G,Ft,Gt,l1,fgss, pf)) {

            fgss[F.vbf_tt_number_of_entries + pf] = 1;
            l2.x = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
            l2.y = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
            for(i=0; i<F.vbf_tt_number_of_entries; i++){
               l2.x[i] = L2.x[i];
               l2.y[i] = L2.y[i];
            }
            /* add its L2 values to L2 guesses. */
            xgs[n]   = Gt.t[1*Gt.tN + g_];
            xgs[n+1] = Gt.t[2*Gt.tN + g_];
            xgs[n+2] = Gt.t[3*Gt.tN + g_];

            /* and assign L2 configuration: */
            assignF(F,G,Ft,Gt,l1,l2,f,g_,fgss,xgs,0,px,cfg);
            delete_linear_from_memory(l2);
         }

         delete_linear_from_memory(l1);
         free(fgss);
         if(g_equivalent) return;
         g_++;
         while(L1.x[Gt.t[g_]]!=0 && g_<Gt.tN) g_++;
      }
   }
   return;
}

/* combine(...) from alg1.c => "combine" with L2 and xgs. */
static void combine(linear L2, vbf_tt_entry *xgs, unsigned char px){
   size_t a,b,i;

   a = (1<<(2*px)) - 1;
   b = a + 3;

   for(i=0; i<a; i+=3){
      /* come up with linear combos and add them to Linears and guesses */
      L2.y[xgs[a]^xgs[i]] = L2.y[xgs[a]] ^ L2.y[xgs[i]];
      L2.x[L2.y[xgs[a]^xgs[i]]] = xgs[a]^xgs[i];
      L2.y[xgs[a+1]^xgs[i+1]] = L2.y[xgs[a+1]] ^ L2.y[xgs[i+1]];
      L2.x[L2.y[xgs[a+1]^xgs[i+1]]] = xgs[a+1]^xgs[i+1];
      L2.y[xgs[a+2]^xgs[i+2]] = L2.y[xgs[a+2]] ^ L2.y[xgs[i+2]];
      L2.x[L2.y[xgs[a+2]^xgs[i+2]]] = xgs[a+2]^xgs[i+2];

      L2.y[xgs[a]^xgs[i+1]] = L2.y[xgs[a]] ^ L2.y[xgs[i+1]];
      L2.x[L2.y[xgs[a]^xgs[i+1]]] = xgs[a]^xgs[i+1];
      L2.y[xgs[a+1]^xgs[i+2]] = L2.y[xgs[a+1]] ^ L2.y[xgs[i+2]];
      L2.x[L2.y[xgs[a+1]^xgs[i+2]]] = xgs[a+1]^xgs[i+2];
      L2.y[xgs[a+2]^xgs[i]] = L2.y[xgs[a+2]] ^ L2.y[xgs[i]];
      L2.x[L2.y[xgs[a+2]^xgs[i]]] = xgs[a+2]^xgs[i];

      L2.y[xgs[a]^xgs[i+2]] = L2.y[xgs[a]] ^ L2.y[xgs[i+2]];
      L2.x[L2.y[xgs[a]^xgs[i+2]]] = xgs[a]^xgs[i+2];
      L2.y[xgs[a+1]^xgs[i]] = L2.y[xgs[a+1]] ^ L2.y[xgs[i]];
      L2.x[L2.y[xgs[a+1]^xgs[i]]] = xgs[a+1]^xgs[i];
      L2.y[xgs[a+2]^xgs[i+1]] = L2.y[xgs[a+2]] ^ L2.y[xgs[i+1]];
      L2.x[L2.y[xgs[a+2]^xgs[i+1]]] = xgs[a+2]^xgs[i+1];

      /* last but not least, add them to guess list as well. */
      xgs[b+3*i]   = xgs[a]^xgs[i];
      xgs[b+3*i+1] = xgs[a+1]^xgs[i+1];
      xgs[b+3*i+2] = xgs[a+2]^xgs[i+2];

      xgs[b+3*i+3] = xgs[a]^xgs[i+1];
      xgs[b+3*i+4] = xgs[a+1]^xgs[i+2];
      xgs[b+3*i+5] = xgs[a+2]^xgs[i];

      xgs[b+3*i+6] = xgs[a]^xgs[i+2];
      xgs[b+3*i+7] = xgs[a+1]^xgs[i];
      xgs[b+3*i+8] = xgs[a+2]^xgs[i+1];

   }
   return;
}

/* generate(...) from alg1.c => linear combos for L1 side from new L2 triplets. */
static size_t generateF(const vbf_tt F, const vbf_tt G, linear L1, linear L2, vbf_tt_entry *fgs, 
                        vbf_tt_entry *xgs, unsigned char px) {

   size_t a,b,i,j,k,n;
   vbf_tt_entry f,g;

   a = (1<<(2*px)) + 2;
   b = (1<<(2*(px+1))) - 1;
   n = 0;
   while(fgs[n]!=0) n++;
   j = n; /* j is a position indicator to return, start of newly added values 
             (the ones that have not been linearly combined yet). */

   for(i=a; i<b; i+=3){
      g = G.vbf_tt_values[xgs[i]];
      f = F.vbf_tt_values[L2.y[xgs[i]]];
      if((f==0 && g!=0)||(g==0 && f!=0)) return 0; /* redundant condition. */
      if(L1.x[g]!=0 && L1.x[g]!=f) return 0;
      if(L1.y[f]!=0 && L1.y[f]!=g) return 0;
      if(L1.y[f]!=0){
         for(k=0; k<n; k++){
            if(fgs[k]==f){
               fgs[F.vbf_tt_number_of_entries + k] = 1;
               break;
            }
         }
      } else {
         fgs[n] = f;
         fgs[F.vbf_tt_number_of_entries + n] = 1;
         n+=1;
         L1.y[f] = g;
         L1.x[g] = f;
      }
   }

   return j;
}

/* configure(...) for L2 assignment from alg1.c */
static void configure(const triplicate Ft, const triplicate Gt, linear L2, size_t f, size_t g,
                      unsigned char xymc, unsigned char cfg) {

   if(cfg==1){
      switch(xymc){
         case 0:
            L2.y[Gt.t[1*Gt.tN + g]] = Ft.t[1*Ft.tN + f];
            L2.x[Ft.t[1*Ft.tN + f]] = Gt.t[1*Gt.tN + g];
            L2.y[Gt.t[2*Gt.tN + g]] = Ft.t[2*Ft.tN + f];
            L2.x[Ft.t[2*Ft.tN + f]] = Gt.t[2*Gt.tN + g];
            L2.y[Gt.t[3*Gt.tN + g]] = Ft.t[3*Ft.tN + f];
            L2.x[Ft.t[3*Ft.tN + f]] = Gt.t[3*Gt.tN + g];
            break;
         case 1:
            L2.y[Gt.t[1*Gt.tN + g]] = Ft.t[2*Ft.tN + f];
            L2.x[Ft.t[2*Ft.tN + f]] = Gt.t[1*Gt.tN + g];
            L2.y[Gt.t[2*Gt.tN + g]] = Ft.t[3*Ft.tN + f];
            L2.x[Ft.t[3*Ft.tN + f]] = Gt.t[2*Gt.tN + g];
            L2.y[Gt.t[3*Gt.tN + g]] = Ft.t[1*Ft.tN + f];
            L2.x[Ft.t[1*Ft.tN + f]] = Gt.t[3*Gt.tN + g];
            break;
         case 2:
            L2.y[Gt.t[1*Gt.tN + g]] = Ft.t[3*Ft.tN + f];
            L2.x[Ft.t[3*Ft.tN + f]] = Gt.t[1*Gt.tN + g];
            L2.y[Gt.t[2*Gt.tN + g]] = Ft.t[1*Ft.tN + f];
            L2.x[Ft.t[1*Ft.tN + f]] = Gt.t[2*Gt.tN + g];
            L2.y[Gt.t[3*Gt.tN + g]] = Ft.t[2*Ft.tN + f];
            L2.x[Ft.t[2*Ft.tN + f]] = Gt.t[3*Gt.tN + g];
            break;
         default: return;
      }
   }
   else {
      switch(xymc){
         case 0:
            L2.y[Gt.t[1*Gt.tN+g]] = Ft.t[2*Ft.tN + f];
            L2.x[Ft.t[2*Ft.tN + f]] = Gt.t[1*Gt.tN+g];
            L2.y[Gt.t[2*Gt.tN+g]] = Ft.t[1*Ft.tN + f];
            L2.x[Ft.t[1*Ft.tN + f]] = Gt.t[2*Gt.tN+g];
            L2.y[Gt.t[3*Gt.tN+g]] = Ft.t[3*Ft.tN + f];
            L2.x[Ft.t[3*Ft.tN + f]] = Gt.t[3*Gt.tN+g];
            break;
         case 1:
            L2.y[Gt.t[1*Gt.tN+g]] = Ft.t[3*Ft.tN + f];
            L2.x[Ft.t[3*Ft.tN + f]] = Gt.t[1*Gt.tN+g];
            L2.y[Gt.t[2*Gt.tN+g]] = Ft.t[2*Ft.tN + f];
            L2.x[Ft.t[2*Ft.tN + f]] = Gt.t[2*Gt.tN+g];
            L2.y[Gt.t[3*Gt.tN+g]] = Ft.t[1*Ft.tN + f];
            L2.x[Ft.t[1*Ft.tN + f]] = Gt.t[3*Gt.tN+g];
            break;
         case 2:
            L2.y[Gt.t[1*Gt.tN+g]] = Ft.t[1*Ft.tN + f];
            L2.x[Ft.t[1*Ft.tN + f]] = Gt.t[1*Gt.tN+g];
            L2.y[Gt.t[2*Gt.tN+g]] = Ft.t[3*Ft.tN + f];
            L2.x[Ft.t[3*Ft.tN + f]] = Gt.t[2*Gt.tN+g];
            L2.y[Gt.t[3*Gt.tN+g]] = Ft.t[2*Ft.tN + f];
            L2.x[Ft.t[2*Ft.tN + f]] = Gt.t[3*Gt.tN+g];
            break;
         default: return;
      }
   }
}

/* assign(...) from alg1.c: tries xymc in [0..2], config L2, generate, check, guess. */
static void assignF(const vbf_tt F, const vbf_tt G, const triplicate Ft, const triplicate Gt, linear L1, linear L2, size_t f, size_t g,
                    vbf_tt_entry *fgs, vbf_tt_entry *xgs, unsigned char xymc, unsigned char px, unsigned char cfg) {

   while(xymc < 3) {
      configure(Ft, Gt, L2, f, g, xymc, cfg); /* choose the assignemnt of xy map out of three possible. */

      /* give a copy of L2 to the functions that will change it. */
      linear l1, l2;
      l1.x = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
      l1.y = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
      l1.N = F.vbf_tt_number_of_entries;
      l2.x = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
      l2.y = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
      l2.N = F.vbf_tt_number_of_entries;

      /* copy of f guesses since we need those clean every time to know how many new asssignments has been made. */
      vbf_tt_entry *fgss = (vbf_tt_entry*) malloc(2*F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));

      for(size_t i=0; i<F.vbf_tt_number_of_entries; i++){
         l1.x[i] = L1.x[i];
         l1.y[i] = L1.y[i];
         l2.x[i] = L2.x[i];
         l2.y[i] = L2.y[i];
         fgss[i]  = fgs[i];
         fgss[F.vbf_tt_number_of_entries + i] = fgs[F.vbf_tt_number_of_entries + i];
      }

      combine(l2, xgs, px); /* linearly combine L2 values to get new calculated triplets. */
      size_t a = generateF(F,G,l1,l2,fgss,xgs,px); /* generate L1 values from new L2 triplets. */
      if(a != 0) {
         if(check(F,G,Ft,Gt,l1,fgss,a)) { /* linearly combine new values in L1 and check for contradiction. */
            guess(F,G,Ft,Gt,l1,l2,fgss,xgs,px+1,cfg); /* if all is good, proceed to the next unasigned guess of L1. */
            if(g_equivalent) {
               free(fgss);
               free(l1.x); free(l1.y);
               free(l2.x); free(l2.y);
               return;
            }
         }
      }
      free(fgss);
      free(l1.x); free(l1.y);
      free(l2.x); free(l2.y);

      xymc += 1;
   }
   return;
}

/* test_triplicate_linear_equivalence(...) from alg1.c, but returning void => sets g_equivalent. */
static void test_triplicate_linear_equivalence(const vbf_tt F, const vbf_tt G, const triplicate Ft, const triplicate Gt) {

   linear L1, L2;

   L1.N = F.vbf_tt_number_of_entries;
   L2.N = F.vbf_tt_number_of_entries;

   L1.x = (vbf_tt_entry*) calloc(F.vbf_tt_number_of_entries, sizeof(vbf_tt_entry));
   L1.y = (vbf_tt_entry*) calloc(F.vbf_tt_number_of_entries, sizeof(vbf_tt_entry));
   L2.x = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
   L2.y = (vbf_tt_entry*) malloc(F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));

   memset(L2.x,0,F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
   memset(L2.y,0,F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));

   size_t f = 0, g_ = 0; /* position tracker in Ft/Gt triplicate for L1 guesses L1(Ft(f)) = Gt(g). */
   unsigned char px=0, xymc=0; /* pointer to x guesses and x to y map configuration for the L2 guesses. */

   /* f guess sequence to remember f guesses and speed up linear combos. */
   vbf_tt_entry *fgs = (vbf_tt_entry*) calloc(2*F.vbf_tt_number_of_entries, sizeof(vbf_tt_entry));
   /* x guess sequence to remember x guesses and speed up linear combos. */
   vbf_tt_entry *xgs = (vbf_tt_entry*) calloc(F.vbf_tt_number_of_entries, sizeof(vbf_tt_entry));

   /* Outer loop from alg1.c: root guess of L1(Ft(0)) = Gt(0..?). */
   while(g_ < Gt.tN) {
      /* make the first guess for L1: */
      L1.y[Ft.t[f]] = Gt.t[g_];
      L1.x[Gt.t[g_]] = Ft.t[f];
      /* remember the guess in sequences: */
      fgs[0] = Ft.t[f];
      fgs[F.vbf_tt_number_of_entries] = 1; /* mark the guess 0 as configured (L2 derived). */
      xgs[0] = Gt.t[1*Gt.tN + g_];
      xgs[1] = Gt.t[2*Gt.tN + g_];
      xgs[2] = Gt.t[3*Gt.tN + g_];
      /* clean L2 for use: */
      memset(L2.x,0,F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
      memset(L2.y,0,F.vbf_tt_number_of_entries*sizeof(vbf_tt_entry));
      /* and guess L2 configuration: */
      assignF(F, G, Ft, Gt, L1, L2, f, g_, fgs, xgs, xymc, px, 1); /* first configuration set. */
      if(g_equivalent) break;
      assignF(F, G, Ft, Gt, L1, L2, f, g_, fgs, xgs, xymc, px, 2); /* second configuration set. */
      if(g_equivalent) break;
      /* clean up after processed guess. */
      L1.y[Ft.t[f]] = 0;
      L1.x[Gt.t[g_]] = 0;
      /* move sideways, pick another g to pair with L1(F(1)). */
      g_++;
   }

   free(fgs);
   free(xgs);
   delete_linear_from_memory(L1);
   delete_linear_from_memory(L2);
}

/* -----------------------------------------------------------------------
   Public functions as declared in the .h
   ----------------------------------------------------------------------- */

bool is_canonical_triplicate_c(vbf_tt *F) {
   if(!F || F->vbf_tt_number_of_entries == 0) {
      return false;
   }
   triplicate T;
   bool result = is_canonical_triplicate_internal(F, &T);
   if(result) {
      /* Freed if success or fail. */
      delete_triplicate_from_memory(T);
   }
   return result;
}

bool check_lin_eq_2x_uniform_3to1(vbf_tt *F, vbf_tt *G) {
   /* Must have same dimension and be canonical triplicates. */
   if(!F || !G) {
      return false;
   }
   if(F->vbf_tt_dimension != G->vbf_tt_dimension) {
      fprintf(stderr, "error: Functions must have the same dimension => not equivalent.\n");
      return false;
   }

   triplicate Ft, Gt;
   if(!is_canonical_triplicate_internal(F,&Ft)) {
      delete_triplicate_from_memory(Ft);
      return false;
   }
   if(!is_canonical_triplicate_internal(G,&Gt)) {
      delete_triplicate_from_memory(Ft);
      delete_triplicate_from_memory(Gt);
      return false;
   }

   g_equivalent = false; /* reset global. */
   test_triplicate_linear_equivalence(*F, *G, Ft, Gt);

   delete_triplicate_from_memory(Ft);
   delete_triplicate_from_memory(Gt);

   return g_equivalent;
}