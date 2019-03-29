#!/bin/sh -ex

# cleans a potentially failed previous test run
[ -d tmp/ ] && rm -rf tmp/

# creates tmp directory
mkdir tmp

clean_diff() {
  sed "s/....-..-..T..:..:..\......./yyyy-mm-ddThh:mm:ss.mmmmmm/g" tmp/$1 | diff - results/$1
}

# nominal test: first test fail, then fix, then ok, then second test ok
../src/heal -d nominal_json -o tmp/nominal_json_status
diff tmp/nominal_json results/nominal_json
clean_diff nominal_json_status

# nominal test, with yaml conf
../src/heal -d nominal_yaml -o tmp/nominal_yaml_status
diff tmp/nominal_yaml results/nominal_yaml
clean_diff nominal_yaml_status

# first kind of error: first test fail, then fix, then fail again
../src/heal -d error1_json -o tmp/error1_status || true
diff tmp/error1 results/error1
clean_diff error1_status

# second kind of error: first test fail, then fix fail
../src/heal -d error2_json -o tmp/error2_status || true
diff tmp/error2 results/error2
clean_diff error2_status

# test of the "fixing" status (requires a certain timing)
echo "../src/heal -d fixing_yaml -o tmp/fixing_status" | at now
sleep 1
clean_diff fixing_status
sleep 2
diff tmp/fixing results/fixing

# error when using the default yaml loader
../src/heal -d error_loader_yaml -o /dev/null

# cleans tmp directory
rm -rf tmp
