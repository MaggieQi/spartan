#/bin/bash

set -x

test_case=$1
profile_worker=0
profile_master=0
dump_timer=0
worker_list=$3
assign_mode=BY_CORE
#assign_mode=BY_NODE
log_level=WARN
cluster=1
optimization=1
opt_parakeet_gen=1
#hosts=172.31.14.148:2,172.31.11.66:2,172.31.3.55:2,172.31.4.130:2,172.31.0.156:2,172.31.0.175:2,172.31.9.142:2,172.31.14.70:2,172.31.8.50:2,172.31.9.167:2,172.31.8.193:2,172.31.0.46:2,172.31.14.203:2,172.31.4.203:2,172.31.4.116:2,172.31.6.175:2,172.31.12.59:2,172.31.10.225:2,172.31.10.237:2,172.31.11.8:2,172.31.13.194:2,172.31.0.207:2,172.31.3.213:2,172.31.3.123:2,172.31.10.193:2,172.31.4.244:2,172.31.2.245:2,172.31.4.222:2,172.31.11.94:2,172.31.8.173:2,172.31.12.49:2,172.31.7.37:2
#hosts=beaker-20:8
hosts=beaker-20:8,beaker-25:8,beaker-24:8,beaker-21:8,beaker-17:4,beaker-15:4,beaker-16:4
tile_assignment_strategy=round_robin
default_rpc_timeout=3000000

function kill_all_python_process {
    killall -uchenqi python;
    machines=`echo $hosts | awk '{split($1, s, ",");for(i=1;i<=length(s);i++) {split(s[i], t, ":");print t[1]}}'`
    for machine in $machines
    do
        echo "$machine"
        ssh $machine -f "killall -uchenqi python;ps -uchenqi | grep python;"
    done
}

if [ $2 = "profile" ] 
then
    #kill_all_python_process
    #python $test_case --cluster=$cluster --worker_list=$worker_list --assign_mode=$assign_mode --profile_worker=$profile_worker --profile_master=$profile_master --log_level=$log_level &> log
    time python $test_case --cluster=$cluster --hosts=$hosts --dump_timer=$dump_timer --use_threads=0 --num_workers=$worker_list --optimization=$optimization --opt_parakeet_gen=$opt_parakeet_gen --worker_list=$worker_list --assign_mode=$assign_mode --tile_assignment_strategy=$tile_assignment_strategy --default_rpc_timeout=$default_rpc_timeout --profile_worker=$profile_worker --profile_master=$profile_master --log_level=$log_level
else
    nosetests -s --nologcapture $test_case &> log
fi
