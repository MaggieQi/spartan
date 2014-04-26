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
opt_parakeet_gen=0
hosts=beaker-20:8,beaker-23:8,beaker-24:8,beaker-21:8,beaker-17:8,beaker-15:8,beaker-16:8,beaker-19:8
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
