#!/bin/sh -ex

# cleans a potentially failed previous test run
[ -d tmp/ ] && rm -rf tmp/

# creates tmp directory
mkdir tmp

clean_diff() {
  sed "s/....-..-..T..:..:..\......./yyyy-mm-ddThh:mm:ss.mmmmmm/g" tmp/$1 | diff - results/$1
}

# nominal test: first test fail, then fix, then ok, then second test ok
../src/heal -c nominal_json -s tmp/nominal_json_status > tmp/nominal_json_output
diff tmp/nominal_json results/nominal_json
clean_diff nominal_json_status
diff tmp/nominal_json_output results/nominal_json_output

# nominal test, with yaml conf
../src/heal -c nominal_yaml -s tmp/nominal_yaml_status > tmp/nominal_yaml_output
diff tmp/nominal_yaml results/nominal_yaml
clean_diff nominal_yaml_status
diff tmp/nominal_yaml_output results/nominal_yaml_output

# first kind of error: first test fail, then fix, then fail again
../src/heal -c error1_json -s tmp/error1_status > tmp/error1_output || true
diff tmp/error1 results/error1
clean_diff error1_status
diff tmp/error1_output results/error1_output

# second kind of error: first test fail, then fix fail
../src/heal -c error2_json -s tmp/error2_status > tmp/error2_output || true
diff tmp/error2 results/error2
clean_diff error2_status
diff tmp/error2_output results/error2_output

# test of the "fixing" status (requires a certain timing)
echo "../src/heal -c fixing_yaml -s tmp/fixing_status > tmp/fixing_output" | at now
sleep 1
clean_diff fixing_status
sleep 2
diff tmp/fixing results/fixing
diff tmp/fixing_output results/fixing_output

# error when using the default yaml loader
../src/heal -c error_loader_yaml -s /dev/null

# testing modes
../src/heal -c modes -s tmp/modes_status > tmp/modes_output
diff tmp/modes results/modes
clean_diff modes_status
diff tmp/modes_output results/modes_output

# cleans tmp directory
rm -rf tmp
