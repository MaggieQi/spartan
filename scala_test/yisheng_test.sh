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

hosts=172.31.0.192:1,172.31.14.112:1,172.31.3.163:1,172.31.10.58:1,172.31.6.4:1,172.31.11.82:1,172.31.8.91:1,172.31.0.26:1,172.31.3.98:1,172.31.11.130:1,172.31.12.34:1,172.31.7.176:1,172.31.13.144:1,172.31.3.193:1,172.31.8.237:1,172.31.10.79:1,172.31.13.255:1,172.31.6.74:1,172.31.15.149:1,172.31.11.159:1,172.31.4.104:1,172.31.8.184:1,172.31.11.31:1,172.31.4.113:1,172.31.8.76:1,172.31.6.79:1,172.31.12.97:1,172.31.3.191:1,172.31.10.201:1,172.31.3.172:1,172.31.13.76:1,172.31.0.246:1


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
