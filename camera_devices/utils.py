import numpy as np

def undistort_points(u, v, K, D, iter_num=5):
    fx, fy, cx, cy = K
    k1, k2, p1, p2, k3, k4, k5, k6 = D

    x = (u - cx) / fx
    y = (v - cy) / fy
    x0, y0 = x.copy(), y.copy()

    for _ in range(iter_num):
        r2 = x**2 + y**2
        r4 = r2**2
        r6 = r2**3
        
        upper = (1 + k1*r2 + k2*r4 + k3*r6)
        lower = (1 + k4*r2 + k5*r4 + k6*r6)
        radial = upper / lower
        
        dx = 2*p1*x*y + p2*(r2 + 2*x**2)
        dy = p1*(r2 + 2*y**2) + 2*p2*x*y
        
        x = (x0 - dx) / radial
        y = (y0 - dy) / radial

    return x, y

