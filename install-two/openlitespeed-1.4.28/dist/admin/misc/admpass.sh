#!/bin/sh

CUR_DIR=`dirname "$0"`
cd $CUR_DIR
CUR_DIR=`pwd`


SUCC=0
cat <<EOF

Please specify the user name of administrator.
This is the user name required to login the administration Web interface.

EOF

printf "%s" "User name [admin]: "
read ADMIN_USER
if [ "x$ADMIN_USER" = "x" ]; then
	ADMIN_USER=admin
fi

cat <<EOF

Please specify the administrator's password.
This is the password required to login the administration Web interface.

EOF

while [ $SUCC -eq "0" ];  do
	printf "%s" "Password: "
	stty -echo
	read PASS_ONE
	stty echo
	echo ""
	if [ `expr "$PASS_ONE" : '.*'` -ge 6 ]; then
		printf "%s" "Retype password: "
		stty -echo
		read PASS_TWO
		stty echo
		echo ""
		if [ "x$PASS_ONE" = "x$PASS_TWO" ]; then
			SUCC=1
		else
			echo ""
			echo "[ERROR] Sorry, passwords does not match. Try again!"
			echo ""
		fi
	else
		echo ""
		echo "[ERROR] Sorry, password must be at least 6 charactors!"
		echo ""
	fi
done


# generate password file

ENCRYPT_PASS=`$CUR_DIR/../fcgi-bin/admin_php -q $CUR_DIR/htpasswd.php $PASS_ONE`
echo "$ADMIN_USER:$ENCRYPT_PASS" > $CUR_DIR/../conf/htpasswd 
if [ $? -eq 0 ]; then
	echo "Administrator's username/password is updated successfully!"
fi

