#!/bin/bash
# usage: run_valgrindtest.sh [ directory_with_valgrind_expected_output (default: ../test/lsr) [ directory_of_compiled_ls_valgrindtest (default: ./test) ] ]
EXPDIR=../test/lsr
EXECDIR=./test
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


valgrind --leak-check=full --track-origins=yes ${EXECDIR}/ls_valgrindtest > test$$.stdout 2> test$$.stderr
diff \
    <(sed -E -e 's/==[0-9]+==/===PID===/' -e 's/(at 0x.*: malloc )\([^(]*\)/\1 (MALLOC LOCATION)/'\
    -e 's/((at)|(by)) 0x.*: /\1 (HEX_ADDR) /' -e 's/(Address) 0x.* (is)/\1 (HEX_ADDR) \2/'\
    -e '/^===PID=== Copyright \(C\) /d' -e '/^===PID=== Using Valgrind-/d'\
    ${EXPDIR}/valgrind.exp.stderr)\
    <(sed -E -e 's/==[0-9]+==/===PID===/' -e 's/(at 0x.*: malloc )\([^(]*\)/\1 (MALLOC LOCATION)/'\
    -e 's/((at)|(by)) 0x.*: /\1 (HEX_ADDR) /' -e 's/(Address) 0x.* (is)/\1 (HEX_ADDR) \2/'\
    -e '/^===PID=== Copyright \(C\) /d' -e '/^===PID=== Using Valgrind-/d'\
    test$$.stderr)\
    > diff.stderr 2>&1
if [[ ($? != 0) ]]
then
    echo FAILED simple comaprison
    echo check file diff.stderr to see if this is a real problem, or compare side by side the files ${EXPDIR}/valgrind.exp.stderr test$$.stderr
    exit 1
fi
diff ${EXPDIR}/valgrind.exp.stdout test$$.stdout > diff.stdout 2>&1
if [[ ($? != 0) ]]
then
    echo FAILED simple comaprison
    echo check file diff.stdout
    exit 1
fi
rm -f diff.stdout diff.stderr test$$.stdout test$$.stderr
exit 0
