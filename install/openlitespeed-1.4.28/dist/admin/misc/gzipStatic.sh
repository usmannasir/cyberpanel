#!/bin/sh
LEVEL=$1
FN=$2
FN_GZ="$FN.lsz"
FN_GZL="$FN.lszl"
FN_GZT="$FN.lszt"

if [ -f $FN_GZL ] || [ -f $FN_GZT ] || [ -f $FN_GZ ]; then
	exit 0
fi

touch $FN_GZL
gzip -c -$LEVEL $FN > $FN_GZT

if [ $? -eq 0 ]; then
	mv $FN_GZT $FN_GZ
else
	rm $FN_GZT
fi
rm $FN_GZL
exit 0