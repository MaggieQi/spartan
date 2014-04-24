#/bin/bash

set -x

test_case=$1
profile_worker=0
profile_master=0
dump_timer=0
assign_mode=BY_CORE
log_level=WARN
cluster=1
worker_list=$2

tile_assignment_strategy=round_robin
default_rpc_timeout=3000000


hosts=172.31.12.59:2,172.31.10.225:2,172.31.10.237:2,172.31.11.8:2,172.31.13.194:2,172.31.0.207:2,172.31.3.213:2,172.31.3.123:2,172.31.10.193:2,172.31.4.244:2,172.31.2.245:2,172.31.4.222:2,172.31.11.94:2,172.31.8.173:2,172.31.12.49:2,172.31.7.37:2

function kill_all_python_process {
    killall -uchenqi python;
    machines=`echo $hosts | awk '{split($1, s, ",");for(i=1;i<=length(s);i++) {split(s[i], t, ":");print t[1]}}'`
    for machine in $machines
    do
        echo "$machine"
        ssh $machine -f "killall -uchenqi python;ps -uchenqi | grep python;"
    done
}

python $test_case --hosts=$hosts --port_base=40000 --cluster=$cluster --dump_timer=$dump_timer --use_threads=0 --num_workers=$worker_list --assign_mode=$assign_mode --tile_assignment_strategy=$tile_assignment_strategy --default_rpc_timeout=$default_rpc_timeout --profile_worker=$profile_worker --profile_master=$profile_master --log_level=$log_level
