#num_workers="32 16 8 4"
num_workers="25 16 9 4"

for i in $num_workers;
do
  ./test.sh $1 profile $i;
done
