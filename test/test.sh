#!/bin/sh -ex

# cleans a potentially failed previous test run
[ -d tmp/ ] && rm -rf tmp/

# creates tmp directory
mkdir tmp

# test nominal
../src/zebr0-icu -c config.json -s tmp/status
diff tmp/nominal results/nominal
sed -e '2d' tmp/status | diff - results/status

# cleans tmp directory
rm -rf tmp
