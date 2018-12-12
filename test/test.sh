#!/bin/sh -ex

# cleans a potentially failed previous test run
[ -d tmp/ ] && rm -rf tmp/

# creates tmp directory
mkdir tmp

# nominal test: first test fail, then fix, then ok, then second test ok
../src/zebr0-icu -c nominal.json -s tmp/nominal_status
diff tmp/nominal results/nominal
sed -e '2d' tmp/nominal_status | diff - results/nominal_status

# first kind of error: first test fail, then fix, then fail again
../src/zebr0-icu -c error1.json -s tmp/error1_status || true
diff tmp/error1 results/error1
sed -e '2d' tmp/error1_status | diff - results/error1_status

# cleans tmp directory
rm -rf tmp
