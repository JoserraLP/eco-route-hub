import numpy as np
from matplotlib import pyplot as plt


def show_consumption(consumption):
    plt.plot(range(len(consumption)), consumption)
    plt.show()


def compare_consumption(engine_based_consumption, experiment_loaded_consumption):
    # Get greater and shorter list
    if len(engine_based_consumption) > len(experiment_loaded_consumption):
        greater_list, shorter_list = engine_based_consumption, experiment_loaded_consumption
    else:
        greater_list, shorter_list = experiment_loaded_consumption, engine_based_consumption

    # Create an array of indices for each list
    x1 = np.linspace(0, 1, len(greater_list))
    x2 = np.linspace(0, 1, len(shorter_list))

    # Interpolate list2 to the length of list1
    interp_func = np.interp(x1, x2, shorter_list)

    plt.plot(x1, greater_list, label="OBD")
    plt.plot(x1, interp_func, label="estimator")
    plt.legend()
    plt.show()
