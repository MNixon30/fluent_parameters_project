#Random Sampling of N-dimentional Space

from skopt.sampler import Lhs
from skopt.space import Space
import numpy as np
import matplotlib.pyplot as plt


def get_sample_points(n_points, lower_bounds: list, upper_bounds: list):
    """Output is a list of points (lists)"""
    if len(lower_bounds) != len(upper_bounds):
        raise ValueError("Bounds must have the same length")

    space = Space([(float(low), float(high)) for low, high in zip(lower_bounds, upper_bounds)])

    lhs = Lhs(lhs_type='classic', criterion='maximin')
    points = lhs.generate(space.dimensions, n_points)

    np.savetxt(r"C:\Users\mitch\Ravens_Racing_CFD\Project\Test_Files\DesignPoints\DesignPoints.csv", points, delimiter=",")
    return np.array(points, dtype=float)


#Run and save to approate file
get_sample_points(10, [-1], [4])
        







