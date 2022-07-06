Server_IP=$(curl --silent --max-time 30 -4 https://cyberpanel.sh/?ip)
echo "$Server_IP" > "/etc/cyberpanel/machineIP"