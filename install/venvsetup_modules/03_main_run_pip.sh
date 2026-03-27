#!/usr/bin/env bash
# install/venvsetup part 3 – main_install_run, pip_virtualenv
main_install_run() {
debug="1"
if [[ $debug == "0" ]] ; then
	echo "/usr/local/CyberPanel/bin/python2 install.py $SERVER_IP $SERIAL_NO $LICENSE_KEY"
	exit
fi

if [[ $debug == "1" ]] ; then
	EXTRA_VER_ARGS=""
	[[ -n "${PHPMYADMIN_VER:-}" ]] && EXTRA_VER_ARGS="$EXTRA_VER_ARGS --phpmyadmin-version ${PHPMYADMIN_VER}"
	[[ -n "${SNAPPYMAIL_VER:-}" ]] && EXTRA_VER_ARGS="$EXTRA_VER_ARGS --snappymail-version ${SNAPPYMAIL_VER}"
	if [[ $DEV == "ON" ]] ; then
	/usr/local/CyberPanel/bin/python install.py $SERVER_IP $SERIAL_NO $LICENSE_KEY --mariadb-version "${MARIADB_VER:-11.8}" $EXTRA_VER_ARGS
	else
	/usr/local/CyberPanel/bin/python2 install.py $SERVER_IP $SERIAL_NO $LICENSE_KEY --mariadb-version "${MARIADB_VER:-11.8}" $EXTRA_VER_ARGS
	fi
	
	if grep "CyberPanel installation successfully completed" /var/log/installLogs.txt > /dev/null; then 
		echo -e "\nCyberPanel installation sucessfully completed..."
else
	echo -e "Oops, something went wrong..."
	exit
fi

if [[ $MEMCACHED == "ON" ]] ; then
	memcached_installation
fi
if [[ $REDIS == "ON" ]] ; then
	redis_installation
fi
	after_install
fi
}

pip_virtualenv() {
if [[ $DEV == "OFF" ]] ; then
if [[ $SERVER_COUNTRY == "CN" ]] ; then
	mkdir /root/.pip
cat << EOF > /root/.pip/pip.conf
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/ 
EOF
fi

if [[ $PROVIDER == "Alibaba Cloud" ]] ; then
	pip install --upgrade pip 2>/dev/null || echo "⚠️  pip upgrade completed with warnings"
	pip install setuptools==40.8.0 2>/dev/null || echo "⚠️  setuptools installation completed with warnings"
fi

pip install virtualenv 2>/dev/null || echo "⚠️  virtualenv installation completed with warnings"

# Create virtual environment with fallback for Ubuntu 22.04 compatibility
echo "Creating CyberPanel virtual environment..."
if python3 -m venv --system-site-packages /usr/local/CyberPanel 2>&1 | grep -q "unrecognized option"; then
    # Fallback to virtualenv if python3 -m venv doesn't support --system-site-packages
    virtualenv --system-site-packages /usr/local/CyberPanel
elif python3 -m venv --system-site-packages /usr/local/CyberPanel 2>/dev/null; then
    echo "Virtual environment created successfully using python3 -m venv"
else
    # Final fallback to virtualenv
    virtualenv --system-site-packages /usr/local/CyberPanel
fi

source /usr/local/CyberPanel/bin/activate
rm -rf requirements.txt
wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/1.8.0/requirments.txt
# Install packages with robust error handling to prevent broken pipe errors
safe_pip_install "pip" "requirements.txt" "--ignore-installed"
# python-dotenv for Django .env loading (upstream f3437739; critical on some AlmaLinux 8 venvs)
pip install python-dotenv 2>/dev/null || echo "⚠️  python-dotenv install skipped or failed"
fi

if [[ $DEV == "ON" ]] ; then
	#install dev branch 
	#wget https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/requirments.txt
	cd /usr/local/
	python3.6 -m venv CyberPanel
	source /usr/local/CyberPanel/bin/activate
	
	# Try to download requirements file with fallback options
	echo "Attempting to download requirements for branch/commit: $BRANCH_NAME"
	
	# First try the specified branch/commit
	if wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/requirments.txt 2>/dev/null; then
		echo "Successfully downloaded requirements from $BRANCH_NAME"
	elif wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/requirments-old.txt 2>/dev/null; then
		echo "Successfully downloaded requirements-old.txt from $BRANCH_NAME"
	elif wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/requirments.txt 2>/dev/null; then
		echo "Fallback: Downloaded requirements from stable branch"
	else
		echo "Warning: Could not download requirements file, using minimal default requirements"
		cat > requirements.txt << 'EOF'
# Minimal CyberPanel requirements - fallback when requirements file is not available
Django==3.2.25
PyMySQL==1.1.0
requests==2.31.0
cryptography==41.0.7
psutil==5.9.6
EOF
	fi
	
	safe_pip_install "pip3.6" "requirements.txt" "--ignore-installed"
	pip3.6 install python-dotenv 2>/dev/null || echo "⚠️  python-dotenv (pip3.6) install skipped or failed"
fi

if [ -f requirements.txt ] && [ -d cyberpanel ] ; then
	rm -rf cyberpanel
	rm -f requirements.txt
fi

if [[ $SERVER_COUNTRY == "CN" ]] ; then
	wget https://cyberpanel.sh/cyberpanel-git.tar.gz
	tar xzvf cyberpanel-git.tar.gz > /dev/null
	cp -r cyberpanel /usr/local/cyberpanel
	cd cyberpanel/install
else
	if [[ $DEV == "ON" ]] ; then
	git clone https://github.com/usmannasir/cyberpanel
	cd cyberpanel
	git checkout $BRANCH_NAME
	cd -
	cd cyberpanel/install
	else
	git clone https://github.com/usmannasir/cyberpanel
	cd cyberpanel/install
	fi
fi
curl https://cyberpanel.sh/?version
}
