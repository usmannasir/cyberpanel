#!/bin/sh

date=`date -u '+%a, %d %b %Y %H:%M:%S %Z'`

cat << EOF
Content-type: text/plain
Expires: $date

CGI printenv

EOF

echo 'Date:'
date
echo
echo 'Id:'
id
echo
echo 'Env:'
printenv
echo
if [ "$CONTENT_LENGTH" != "" ] ; then
    if [ "$CONTENT_LENGTH" -ne 0 ] ; then
	echo 'Input:'
	echo
	dd bs=1 count=$CONTENT_LENGTH
	echo
    fi
fi
