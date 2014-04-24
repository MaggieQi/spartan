#!/bin/bash
curdir=`pwd`
dirs="tests spartan spartan/array spartan/examples spartan/expr spartan/rpc" 
for dir in $dirs
do
    workdir="$curdir/$dir"
    cd $workdir
    rm -f *.so *.cpp *.c *.pyc
done
