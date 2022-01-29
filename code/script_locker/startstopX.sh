#!/bin/bash
# example start up script which converts any existing .h264 files into MP4
# Edited by Lui. The trap doesnt always catch the exit, and that causes mayhem since
# since no conversion never resume. Probably brown outs or unexpected shutdowns make this happen.
# Since startstopX.sh only runs on startup, it seems rational that it needs not worry about the flag.
# The scrip is revised to run regardless of flag, but still set it spo that the boxing script does get blocked.

MACRODIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BASEDIR="$( cd "$( dirname "${MACRODIR}" )" >/dev/null 2>&1 && pwd )"
mypidfile=${MACRODIR}/startstop.sh.pid
mylogfile=${BASEDIR}/scheduleLog.txt

#Remove PID file when exiting
trap "rm -f -- '$mypidfile'" EXIT


#Check if script already running
NOW=`date +"-%Y/%m/%d %H:%M:%S-"`
if [ -f $mypidfile ]; then
        echo "${NOW} Boxing flag already exists, but because this is a startup script, running anyway. Flag will be cleared when done" >> ${mylogfile}
#        exit   #LUI: dont exit. easy
fi

echo $$ > "$mypidfile"

#Do conversion
if [ "$1" == "start" ]; then
  cd ${MACRODIR}
  cd ../media
  shopt -s nullglob
  for f in *.h264
    do
      f1=${f%.*}.mp4
      #p=${f%.*}.h264.*.th.jpg
        NOW=`date +"-%Y/%m/%d %H:%M:%S-"`
        echo "${NOW} Converting $f" >> ${mylogfile}
        #set -e;MP4Box -fps 25 -add $f $f1 > /dev/null 2>&1;rm $f;
        if MP4Box -fps 25 -add $f $f1; then
                NOW=`date +"-%Y/%m/%d %H:%M:%S-"`
                echo "${NOW} Conversion complete, removing $f" >> ${mylogfile}
                for p in ${f%.*}.h264.*.th.jpg;
                   do mv "$p" $(echo "$p" | sed 's/h264/mp4/g');
                   #echo "${NOW} Renaming thumbnail $p" >> ${mylogfile}
                done
                rm $f
        else
                NOW=`date +"-%Y/%m/%d %H:%M:%S-"`
                echo "${NOW} Error with $f" >> ${mylogfile}
        fi
    done
  for f in *.h264.*.th.jpg;
    do mv "$f" $(echo "$f" | sed 's/h264/mp4/g');
    #echo "${NOW} Renaming thumbnail in the end... $f" >> ${mylogfile}
  done
fi
