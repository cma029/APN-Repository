Directory:
cd c_src

# Build check_lin_eq_2x_uniform_3to1.c => libcheck_lin_eq_2x_uniform_3to1.so
gcc -shared -fPIC check_lin_eq_2x_uniform_3to1.c -o libcheck_lin_eq_2x_uniform_3to1.so

# Build spectra_computations.c => libspectra_computations.so
gcc -shared -fPIC spectra_computations.c -o libspectra_computations.so

# Build invariants_computations.cpp => libinvariants_computations.so
g++ -std=c++11 -fPIC -shared -o libinvariants_computations.so invariants_computations.cpp