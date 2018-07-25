#!/usr/bin/env bash

for node in {0..8}
do
    ssh pacifix${node} "uname -a" & 
    #ssh -v pacifix${node} "uname -a" >sshlog.$$
done

#for item in {0..10}
#do
#    #ssh pacifix1 "uname -a" &
#    #ssh 134.104.70.91 "uname -a" &
#    ssh pacifix1.mpifr-bonn.mpg.de "uname -a" &
#done
