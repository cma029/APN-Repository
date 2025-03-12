# APN Repository Manual

## 1. Introduction

This repository provides a CLI‐based tool for handling APNs (Almost Perfect Nonlinear functions) in various finite fields GF(2^n), with multiple invariants (rank computations, ortho-derivative spectra, etc.) and equivalence checks (CCZ, linear 3‐to‐1). All commands are run via main.py.

Important: The code uses univariate polynomials (poly) as its core representation for APNs (especially for storing in the database). The fastest, recommended approach for bulk input is --poly-file. Be aware that computing some of the invariants (like the ranks) requires a significant amount of free memory.

## 2. Basic Program Flow

Below is a rough diagram showing how an APN flows through the system:

```
        +------------------------+
        | add-input             |
        | - read polynomials    |
        | - check is_apn        |
        +------------------------+
                   |
                   v
        +------------------------+
        | compare               |
        | - compare invariants  |
        | - narrow matches      |
        +------------------------+
                   |
                   v
        +------------------------+
        | equivalence checks    |
        |  of the matches       |
        |  (ccz, uni3to1, etc.) |
        +------------------------+
                   |
                   v
   If no equivalence is found, then your APN is probably new.
   Alternatively there is a match/equivalence and the APN is known.
```

1. **add-input**: Takes polynomials/truth tables, does a check for `is_apn`.
2. **compare**: Compares invariants with the database. Computes them for the input if needed. We match the input APN(s) and database APN(s) based on invariants and narrow the number of matches by introducing more invariants.
3. **equivalence checks**: CCZ or uni3to1 (plus potential future algorithms). If there are matches left after the compare phase, then run the equivalence check on those matches. If the matching APN is found not equivalent, we remove it from the match list. If an APN is found equivalent to a known APN, we remove it from the input file because it’s not new.
4. If no match remain after the match and equivalence checks, your APN is likely a brand-new function.

The `print` command shows you the details at any stage.

## 3. Installation

### 3.1 Basic Requirements

You need:

- Python 3 (3.11 or later recommended)
- SageMath for rank computations and CCZ equivalence check

Example setup on Linux:

```
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh

conda create -n sage sage python=3.12
conda activate sage
sage
```

See https://doc.sagemath.org/html/en/installation/index.html for details.

Also install a few Python libraries:

```
python3 -m pip install galois click pandas fastparquet
```

(Or install them inside your conda environment.)

### 3.2 Precompiled Libraries

Inside c_src/, we provide Linux .so shared libraries:

- libcheck_lin_eq_2x_uniform_3to1.so
- libspectra_computations.so
- libinvariants_computations.so

If you need to recompile for macOS/Windows or rebuild them on Linux, see the Appendix below.

## 4. Memory and Concurrency

Most commands include --max-threads <N> (default unlimited).

With regard to the concurrency:
1) Spawns multiple processes for parallel tasks (is_apn checks, ortho-derivative spectra, rank computations, equivalences).
2) Memory usage can be very large for rank computations (delta, gamma). For GF(2^8), each thread might need ~33 GB free RAM.
3) If you have limited memory, pick fewer threads (e.g. --max-threads=1). If you have more resources, use more threads for speed.

## 5. Commands Overview

Run commands via:

```
python main.py <command> [options...]
```

### 5.1 add-input

```
python main.py add-input
  --poly <tuple> ...       
  --field-n <int>
  --irr-poly <string>
  --tt-file <path> ...
  --poly-file <path> ...
  --citation <str> ...
  --citation-all <str>
  --max-threads <int>
```

- Reads APNs from inline polynomials (--poly), polynomial files (--poly-file), or truth tables (--tt-file).
- The first line of the files (--poly-file, --tt-file) needs to be a single integer representing the field n dimension.
- Tests new APNs in concurrency to see if differential uniformity=2. Non-APNs are skipped.
- Recommended: --poly-file for speed, since the database uses univariate polynomial representation.

### 5.2 compare

```
python main.py compare
  --type [odds|odws|delta|gamma|all]
  --field-n <int>
  --max-threads <int>
```

- Compares invariants of input APNs vs. the database for dimension <field-n>.
- If an APN has existing matches, those are narrowed by checking new invariants. A full database search is done for first compare.
- Warning: using delta/gamma rank for GF(2^8) can require ~33 GB per thread. Ranks are not possible for fields > 10.

### 5.3 compute-input-invariants

```
python main.py compute-input-invariants
  --index <int>
  --max-threads <int>
```

- Computes all invariants (ortho-derivative-spectra, rank, etc.) for input APNs only. If --index <N>, processes just that APN.
- Warning: using delta/gamma rank for GF(2^8) can require ~33 GB per thread. Ranks are not possible for fields > 10.

### 5.4 print

```
python main.py print
  --index <int>
  --summary
  --input-only
```

- Prints your input APNs from storage/input_apns_and_matches.json.
- By default, prints each APN + all matches. 
- --summary shows how many matches per APN.
- --input-only omits matches entirely.
- Combine --index <N> to see one APN only.

### 5.5 read-db

```
python main.py read-db
  --field-n <int>
  --range <start> <end>
```

- Loads APNs from the Parquet database for GF(2^n).
- If --range is provided, prints a subset of APNs.

### 5.6 reset-storage

```
python main.py reset-storage [--yes]
```

- Deletes input_apns_and_matches.json and equivalence_list.json.

### 5.7 save-matches

```
python main.py save-matches --output-file <jsonfile>
```

- Exports the current matches for each input APN to a JSON file.

### 5.8 store-input

```
python main.py store-input
  [--index <int>]
  [--max-threads <int>]
```

- Computes invariants for your input APNs (or only one APN if --index is given).
- Then stores them in the Parquet database if they are valid and not duplicates.
- If multiple APNs have different field_n, the code aborts. Also concurrency-enabled.

### 5.9 ccz

```
python main.py ccz
  [--index <int>]
  [--max-threads <int>]
```

- Checks CCZ equivalence for input APNs and matches (or only one input APN if --index is given).
- If the CCZ equivalence is True => we remove that input APN, if False => we remove the inequivalent match (narrowing).
- CCZ equivalence is a ‘one size fits all’ option, but the drawback is that it's very slow.

### 5.10 uni3to1

```
python main.py uni3to1
  [--index <int>]
  [--max-threads <int>]
```

- Ensure k_to_1 is computed so the code recognizes them as "3-to-1".
- Checks linear equivalence for APNs with uniform k_to_1 == "3-to-1". If found, removes that input APN. If False, remove match.
- The uni3to1 equivalence check is really fast, but the drawback is that it only works for APN(s) with the 3-to-1 uniform distribution.

## 6. Memory & Thread Settings

Use --max-threads <N> to limit concurrency and reduce memory usage. If a rank in GF(2^8) takes ~33GB per thread, then 2 threads is ~66GB total. Adjust accordingly to your system’s capacity.

## 7. Appendix: Building Shared Libraries

### 7.1 Linux

We already provide .so files under c_src/. If you need to rebuild:

```
cd c_src

# Build check_lin_eq_2x_uniform_3to1.c => libcheck_lin_eq_2x_uniform_3to1.so
gcc -shared -fPIC check_lin_eq_2x_uniform_3to1.c -o libcheck_lin_eq_2x_uniform_3to1.so

# Build spectra_computations.c => libspectra_computations.so
gcc -shared -fPIC spectra_computations.c -o libspectra_computations.so

# Build invariants_computations.cpp => libinvariants_computations.so
g++ -std=c++11 -fPIC -shared -o libinvariants_computations.so invariants_computations.cpp
```

### 7.2 macOS

Use .dylib instead of .so. For instance:
```
cd c_src
gcc -std=c99 -shared -fPIC -o libcheck_lin_eq_2x_uniform_3to1.dylib check_lin_eq_2x_uniform_3to1.c
```
(You may need -dynamiclib on some toolchains.)

### 7.3 Windows

Use .dll. For example:
```
cd c_src
gcc -shared -o check_lin_eq_2x_uniform_3to1.dll check_lin_eq_2x_uniform_3to1.c
```
Typically omit -fPIC on Windows and possibly create an import library.