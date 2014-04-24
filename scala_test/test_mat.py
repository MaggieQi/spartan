import numpy as np
import time

M = 40000 #20000
N = 2500 #20000 
C = 1
a = np.random.randn(M, N)
b = np.random.randn(N, C)

print "begin"

st = time.time()
a.dot(b)
print time.time() - st
