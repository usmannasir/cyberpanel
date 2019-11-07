#!/bin/bash

USER="root"
PASSWORD="1d1bb076c3bd9ae9ef545e3eafb1a35c68d3c5f4a6c03862"
#OUTPUT="/Users/rabino/DBs"
cd /mnt/HC_Volume_2760413

#rm "$OUTPUTDIR/*gz" > /dev/null 2>&1

databases=`mysql -u $USER -p$PASSWORD -e "SHOW DATABASES;" | tr -d "| " | grep -v Database`
mkdir `date +%Y%m%d`

for db in $databases; do
    if [[ "$db" != "information_schema" ]] && [[ "$db" != "performance_schema" ]] && [[ "$db" != "mysql" ]] && [[ "$db" != _* ]] ; then
        echo "Dumping database: $db"
        mysqldump -u $USER -p$PASSWORD --databases $db > `date +%Y%m%d`/`date +%Y%m%d`.$db.sql
       # gzip $OUTPUT/`date +%Y%m%d`.$db.sql
    fi
done