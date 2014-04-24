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

hosts=beaker-18:4,beaker-19:4,beaker-16:4,beaker-15:4,beaker-23:4,beaker-24:4,beaker-20:4,beaker-22:4


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
