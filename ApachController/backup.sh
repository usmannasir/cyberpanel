#!/bin/bash

USER="${MYSQL_USER:-root}"
PASSWORD="${MYSQL_PASSWORD:-}"
# Check if password is provided via environment variable or prompt for it
if [[ -z "$PASSWORD" ]]; then
    echo -n "Enter MySQL password: "
    read -r -s PASSWORD
    echo
fi
#OUTPUT="/Users/rabino/DBs"
cd /mnt/HC_Volume_2760413 || exit

#rm "$OUTPUTDIR/*gz" > /dev/null 2>&1

databases=$(mysql -u "$USER" -p"$PASSWORD" -e "SHOW DATABASES;" | tr -d "| " | grep -v Database)
mkdir "$(date +%Y%m%d)"

for db in $databases; do
    if [[ "$db" != "information_schema" ]] && [[ "$db" != "performance_schema" ]] && [[ "$db" != "mysql" ]] && [[ "$db" != _* ]] ; then
        echo "Dumping database: $db"
        mysqldump -u "$USER" -p"$PASSWORD" --databases "$db" > "$(date +%Y%m%d)/$(date +%Y%m%d).$db.sql"
       # gzip $OUTPUT/$(date +%Y%m%d).$db.sql
    fi
done