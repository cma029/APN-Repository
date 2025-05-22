# VBF Repository Manual

## 1. Introduction

This repository provides a CLI‐based tool for handling Vectorial Boolean Functions (VBFs) with spesial attention on Almost Perfect Nonlinear functions (APNs) in various finite fields GF(2^n), with multiple invariants (rank computations, ortho-derivative spectra, etc.) and equivalence checks (CCZ, linear 3‐to‐1). All commands are run via `main.py`.

Important: The code uses univariate polynomials (poly) as its core representation for VBFs (especially for storing in the database). The fastest, recommended approach for bulk input is `--poly-file`. Be aware that computing some of the invariants (like the ranks) requires a significant amount of free memory.

## 2. Basic Program Flow

Below is a rough diagram showing how a candidate function flows through the platform:

```
        +-----------------------------------+
        | add-input                         |
        | - import polynomials              |
        | - compute differential uniformity | 
        | - check is_apn                    |
        +-----------------------------------+
                        |
                        v
        +-----------------------------------+
        | compare                           |
        | - compute invariants for input    |
        | - compare selected invariants     |
        | - narrow matches (rounds)         |
        +-----------------------------------+
                        |
                        v
        +-----------------------------------+
        | equivalence tests of the matches  |
        | - (ccz, uni3to1, etc.)            |
        +-----------------------------------+
                        |
                        v
   If no equivalence is found, then your VBF is probably new.
   Alternatively there is a match/equivalence and the VBF is known.
```

1. **add-input**: Takes polynomials/truth tables, compute the differential uniformity and does a check for `is_apn`.
2. **compare**: Compares invariants with the database. Computes them for the input if needed. We match the input candidate VBF(s) and database VBF(s) based on invariants and narrow the number of matches by introducing more invariants.
3. **equivalence checks**: CCZ or uni3to1 (plus potential future algorithms). If there are matches left after the compare phase, then run the equivalence check on those matches. If the matching VBF is found not equivalent, we remove it from the match list. If an VBF is found equivalent to a known VBF, we remove it from the input file and store it under confirmed equivalence because it’s not new.
4. If no match remain after the match and equivalence tests, your VBF is likely a brand-new function.

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

Inside `c_src/`, we provide Linux `.so` shared libraries:

- `libcheck_lin_eq_2x_uniform_3to1.so`
- `libspectra_computations.so`
- `libinvariants_computations.so`

If you need to recompile for macOS/Windows or rebuild them on Linux, see the Appendix below.

## 4. Memory and Concurrency

Most commands include `--max-threads <N>` (default: all available cores).

With regard to the concurrency:
1. Spawns multiple processes for parallel tasks (is_apn checks, ortho-derivative spectra, rank computations, equivalences).
2. Memory usage can be very large for rank computations (delta, gamma). For GF(2^8), each thread might need ~33 GB free RAM.
3. If you have limited memory, pick fewer threads (e.g. `--max-threads=1`). If you have more resources, use more threads for speed.

## 5. Commands Overview

Run commands via:

```bash
python main.py <command> [options...]
```

### 5.1 add-input

```bash
python main.py add-input
  --poly <tuple> ...       
  --dim <int>
  --irr-poly <string>
  --tt-file <path> ...
  --poly-file <path> ...
  --citation <str> ...
  --citation-all <str>
  --max-threads <int>
```

- Reads VBFs from inline polynomials (`--poly`), polynomial files (`--poly-file`), or truth tables (`--tt-file`).
- The polynomial files (`--poly-file`) option accepts coefficients `'a'-'z'` (consistently) and the monomial must be `'x'`.
- The first line of the files (`--poly-file`, `--tt-file`) needs to be a single integer representing the field `n` dimension.
- Tests new VBFs in concurrency to see if `differential uniformity=2`.
- Attach citations to each VBF with `--citation` (inline, in order) or `--citation-all` (same citation for all VBFs in a file).
- Recommended: `--poly-file` for speed, since the database uses the univariate polynomial representation.

### 5.2 compare

```bash
python main.py compare
  --type [odds|odws|delta|gamma|all]
  --max-threads <int>
```

- Compares invariants of input VBFs vs. the database for GF(2^n) based on the dimension.
- If an VBF has existing matches, those are narrowed by checking new invariants. A full database search is done for a first compare.
- Warning: using delta/gamma rank for GF(2^8) can require ~33 GB per thread. Ranks are not default enabled for fields > 8.

### 5.3 compute-input-invariants

```bash
python main.py compute-input-invariants
  --index <int>
  --max-threads <int>
```

- Computes all invariants (ortho-derivative-spectra, rank, etc.) for input VBFs only. If `--index <N>`, processes just that VBF.
- Warning: using delta/gamma rank for GF(2^8) can require ~33 GB per thread. Ranks are not default enable for fields > 8.

### 5.4 print

```bash
python main.py print
  --index <int>
  --summary
  --input-only
```

- Prints your input VBFs from `storage/input_vbfs_and_matches.json`.
- By default, prints each VBF + all matches. 
- `--summary` shows how many matches per VBF.
- `--input-only` omits matches entirely.
- Combine `--index <N>` to see one VBF only.

### 5.5 read-db

```bash
python main.py read-db
  --dim <int>
  --range <start> <end>
  --save-to-file
```

- Loads VBFs from the Parquet database for GF(2^n) and displays them.
- **Required**:
  - `--dim <int>`: The integer field n dimension for GF(2^n).
- **Options**:
  - `--range <start> <end>` : Displays a subset of VBFs in the requested index range (1-based). **The default** is that the first **5** VBFs are printed to the screen if no range is specified.
  - `--save-to-file` : Writes the univariate polynomial strings of all loaded VBFs to a file `{dim}bit_db_unipoly.txt`. The first line contains the field n dimension, and each subsequent line has the univariate polynomial string of one VBF:
    1. If `--range` is also supplied, only that subset is shown on screen **and** saved to the file.
    2. If `--range` is not supplied, the script prints up to **5** VBFs on screen but saves all loaded VBFs from the database to the file.

**Examples**:

- Print the first 5 VBFs for GF(2^8):
  ```bash
  python main.py read-db --dim 8
  ```

- Print VBFs #5 through #10 for GF(2^6):
  ```bash
  python main.py read-db --dim 6 --range 5 10
  ```

- Load GF(2^8) VBFs and save only #3–#7 to `8bit_db_unipoly.txt`:
  ```bash
  python main.py read-db --dim 8 --range 3 7 --save-to-file
  ```

### 5.6 reset-storage

```bash
python main.py reset-storage
  --yes
```

- Deletes `input_vbfs_and_matches.json` and `equivalence_list.json`.

### 5.7 save

```bash
python main.py save
  --matches
  --poly
  --tt
  --file-name <str>
```

- The 'save' command can export data from **input** VBF(s) in `input_vbfs_and_matches.json`.
- **Options**:
  - `--matches`: Exports your **input** VBF(s) and **matches** (if any) to a JSON file.
  - `--poly`: Exports all **input** VBF(s) as a list in **Univariate Polynomial Representation**.
  - `--tt`: Exports all **input** VBF(s) as a list of **Truth Tables**.
  - `--file-name`: If only one of `--matches`, `--poly`, or `--tt` is chosen, you can override its default output filename.

If multiple flags are used, each type uses its own default name (e.g. `matches_output.json`, `poly_output.txt`, `tt_output.txt`). When exporting with `--poly` or `--tt`, any dimension mismatch among VBFs causes an error and the command aborts without writing a file. This ensures consistency of dimension in the exported data.

### 5.8 store-input

```bash
python main.py store-input
  --index <int>
  --max-threads <int>
```

- Computes invariants for your input VBFs (or only one VBF if `--index` is given).
- Then stores them in the Parquet database if they are valid and not duplicates.
- If multiple VBFs have different `dim`, the code aborts. Also concurrency-enabled.

### 5.9 ccz

```bash
python main.py ccz
  --index <int>
  --max-threads <int>
```

- Checks CCZ equivalence for input VBFs and matches (or only one input VBF if `--index` is given).
- If the CCZ equivalence is True => we remove that input VBF, if False => we remove the inequivalent match (narrowing).
- CCZ equivalence is a ‘one size fits all’ option, but the drawback is that it's very slow.

### 5.10 uni3to1

```bash
python main.py uni3to1
  --index <int>
  --max-threads <int>
```

- Ensure `k_to_1` is computed so the code recognizes them as "3-to-1".
- Checks linear equivalence for VBFs with uniform `k_to_1 == "3-to-1"`. If equivalence is found, removes that input VBF. If False, remove match.
- The uni3to1 equivalence check is really fast, but the drawback is that it only works for VBF(s) with the 3-to-1 uniform distribution.

### 5.11 export-html

```bash
python main.py export-html
  --dim <int>
  --file-name <str>
```

- Exports the VBF database for GF(2^n) to an HTML file, 500 rows per page.
- **Required**:
  - `--dim <int>`: The integer field n dimension for GF(2^n).
- **Options**:
  - `--file-name <str>`: If omitted, defaults to `vbf_n.html`, where `n` is the dimension.
- The HTML table includes univariate polynomial, ODDS, ODWS, and—if `n <= 9`—the delta rank and gamma rank columns. 
- Also displays citations in a clickable dialog box and uses simple pagination.

## 6. Memory & Thread Settings

Use `--max-threads <N>` to limit concurrency and reduce memory usage. If a rank in GF(2^8) takes ~33GB per thread, then 2 threads is ~66GB total. Adjust accordingly to your system’s capacity.

## 7. Appendix: Building Shared Libraries

### 7.1 Linux

We already provide `.so` files under `c_src/`. If you need to rebuild:

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

Use `.dylib` instead of `.so`. For instance:

```
cd c_src
gcc -std=c99 -shared -fPIC -o libcheck_lin_eq_2x_uniform_3to1.dylib check_lin_eq_2x_uniform_3to1.c
```

(You may need `-dynamiclib` on some toolchains.)

### 7.3 Windows

Use `.dll`. For example:

```
cd c_src
gcc -shared -o check_lin_eq_2x_uniform_3to1.dll check_lin_eq_2x_uniform_3to1.c
```

Typically omit `-fPIC` on Windows and possibly create an import library.