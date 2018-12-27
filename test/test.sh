#!/bin/sh -ex

# cleans a potentially failed previous test run
[ -d tmp/ ] && rm -rf tmp/

# creates tmp directory
mkdir tmp

clean_diff() {
  sed "s/....-..-..T..:..:..\......./yyyy-mm-ddThh:mm:ss.mmmmmm/g" tmp/$1 | diff - results/$1
}

# nominal test: first test fail, then fix, then ok, then second test ok
../src/zebr0-icu -c nominal.json -s tmp/nominal_json_status
diff tmp/nominal_json results/nominal_json
clean_diff nominal_json_status

# nominal test, with yaml conf
../src/zebr0-icu -c nominal.yaml -s tmp/nominal_yaml_status
diff tmp/nominal_yaml results/nominal_yaml
clean_diff nominal_yaml_status

# first kind of error: first test fail, then fix, then fail again
../src/zebr0-icu -c error1.json -s tmp/error1_status || true
diff tmp/error1 results/error1
clean_diff error1_status

# second kind of error: first test fail, then fix fail
../src/zebr0-icu -c error2.json -s tmp/error2_status || true
diff tmp/error2 results/error2
clean_diff error2_status

# cleans tmp directory
rm -rf tmp
