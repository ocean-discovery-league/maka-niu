#!/bin/bash
for FILE in /var/www/html/media/*.mp4
do
        echo "Processing ${FILE}"
        python3 ./TatorUpload.py --type_id 28 --media_path $FILE
done
