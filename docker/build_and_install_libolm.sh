#!/usr/bin/env sh
#
# Call with the following arguments:
#
#    ./build_and_install_libolm.sh <libolm version> <folder to install to>
#
# Example:
#
#    ./build_and_install_libolm.sh 3.1.4 /olm
#
set -ex

# Download the specified version of libolm
git clone -b "$1" https://gitlab.matrix.org/matrix-org/olm.git "$2" && cd "$2"

# Build libolm
cmake . -Bbuild
cmake --build build

# Install
make install

# Build the python3 bindings
cd python && make olm-python3

# Install python3 bindings
make install-python3
