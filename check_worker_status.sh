#!/bin/bash

cat worker.cnf | while read LINE
do
    ip=`echo "$LINE" | awk '{print $1}'`
    host=$ip
    
    echo "Checking server $host..."
    ssh $host $" ps aux | pgrep python >/dev/null && echo 'Normal, Memory usage %, CPU usage %: ' &&  ps aux | \
      grep python | grep -v grep |  awk '{print \$4; print \$3}' \
      || echo 'no process found!'" &
    sleep 1 

done

wait
