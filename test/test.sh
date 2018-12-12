#!/bin/sh -ex

# cleans a potentially failed previous test run
[ -d tmp/ ] && rm -rf tmp/

# creates tmp directory
mkdir tmp

# nominal test: first test fail, then fix, then ok, then second test ok
../src/zebr0-icu -c nominal.json -s tmp/nominal_status
diff tmp/nominal results/nominal
sed -e '2d' tmp/nominal_status | diff - results/nominal_status

# cleans tmp directory
rm -rf tmp
