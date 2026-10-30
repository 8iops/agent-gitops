#!/bin/sh
set -eu
umask 077
# Exercise the real root-owned PVC with a tar that includes its '.' entry.
[ "$(id -u)" = 2000 ]
[ "$(stat -c%u /restore)" = 0 ]
[ ! -e /restore/.synthetic-v2 ]
mkdir -m 700 /restore/.synthetic-v2
trap 'rm -f /restore/.synthetic-v2/probe; rmdir /restore/.synthetic-v2' EXIT
mkdir /work/source
printf 'owned directory extraction probe\n' > /work/source/probe
tar --numeric-owner -C /work/source -cf /work/synthetic.tar .
[ "$(tar -tf /work/synthetic.tar | head -n1)" = ./ ]
tar --no-same-owner -C /restore/.synthetic-v2 -xf /work/synthetic.tar
cmp /work/source/probe /restore/.synthetic-v2/probe
[ "$(stat -c%u /restore)" = 0 ]
[ "$(stat -c%u /restore/.synthetic-v2)" = 2000 ]
printf 'root_owned_parent=preserved tar_dot_entry=verified owned_subdirectory_roundtrip=pass\n'
