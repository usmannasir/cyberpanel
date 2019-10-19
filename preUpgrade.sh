if [ ! -d "/usr/local/CyberPanel" ]; then
  virtualenv --system-site-packages /usr/local/CyberPanel
  source /usr/local/CyberPanel/bin/activate
  rm -rf requirments.txt
  wget https://raw.githubusercontent.com/usmannasir/cyberpanel/1.8.0/requirments.txt
  pip install --ignore-installed -r requirments.txt
  virtualenv --system-site-packages /usr/local/CyberPanel
fi
rm -rf upgrade.py
wget https://raw.githubusercontent.com/usmannasir/cyberpanel/1.8.0/plogical/upgrade.py
/usr/local/CyberPanel/bin/python2 upgrade.py