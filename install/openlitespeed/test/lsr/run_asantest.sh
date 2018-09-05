#!/bin/bash
# usage: run_asantest.sh [ directory_with_valgrind_expected_output (default: ../test/lsr) [ directory_of_compiled_ls_valgrindtest (default: ./test) [ location_of_symbolizer ] ] ]
EXPDIR=../test/lsr
EXECDIR=./test
SYMBOLIZER=$(ls -l /usr/lib/llvm-*/bin/llvm-symbolizer | tail -1 | sed s'/.*\/usr/\/usr/')

if [[ ($# -gt 0) ]]
then
    EXPDIR=$1
    shift
fi
if [[ ($# -gt 0) ]]
then
    EXECDIR=$1
    shift
fi
if [[ ($# -gt 0) ]]
then
    SYMBOLIZER=$1
    shift
fi

export ASAN_SYMBOLIZER_PATH=$SYMBOLIZER
export ASAN_OPTIONS=halt_on_error=0
${EXECDIR}/ls_valgrindtest 1> test$$.stdout 2> test$$.stderr

diff \
    <(sed -E\
    -e 's/==[0-9]+==/===PID===/'\
    -e 's/0x[0-9a-fA-F]*/0x(HEX_ADDR)/g'\
    ${EXPDIR}/asan.exp.stderr)\
    <(sed -E\
    -e 's/==[0-9]+==/===PID===/'\
    -e 's/0x[0-9a-fA-F]*/0x(HEX_ADDR)/g'\
    test$$.stderr)\
    > diff.stderr 2>&1
if [[ ($? != 0) ]]
then
    echo FAILED simple comaprison
    echo check file diff.stderr to see if this is a real problem, or compare side by side the files ${EXPDIR}/asan.exp.stderr test$$.stderr
    exit 1
fi
diff ${EXPDIR}/asan.exp.stdout test$$.stdout > diff.stdout 2>&1
if [[ ($? != 0) ]]
then
    echo FAILED simple comaprison
    echo check file diff.stdout
    exit 1
fi
rm -f diff.stdout diff.stderr test$$.stdout test$$.stderr
exit 0
