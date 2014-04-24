import spartan
from spartan.examples.sklearn.ensemble import RandomForestClassifier
#from sklearn.ensemble import RandomForestClassifier
from datasource import load_data
from spartan import expr
import time

N_TREES = 50

ctx = spartan.initialize()

try:
  x, y = load_data("cf100")
  X = expr.from_numpy(x, tile_hint=(x.shape[0]/ctx.num_workers, x.shape[1])).force()
  Y = expr.from_numpy(y, tile_hint=(x.shape[0]/ctx.num_workers, )).force()
  
  estimators_per_worker = 1 
  
  st = time.time()
  f = RandomForestClassifier(n_estimators=estimators_per_worker * ctx.num_workers, bootstrap=False)
  f.fit(x, y)
  print time.time() - st
  print "!"

finally:
  ctx.shutdown()
