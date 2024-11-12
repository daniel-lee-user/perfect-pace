import numpy as np
from enum import Enum

class Unit(Enum):
    METRIC = 1
    IMPERIAL = 2

class SmoothingMethod(Enum):
    BOX = 1
    GAUSSIAN = 2

class SegmentType(Enum):
    UNIFORM = 1
    VARIABLE = 2
    FIXED_LENGTH = 3

class Conversions(Enum):
    METERS_TO_MILES = 0.0006213712
    METERS_TO_FEET = 3.28084
    MILES_TO_FEET = 5280
    MILES_TO_METERS = 1609.34
    FEET_TO_MILES = 0.000189394
    FEET_TO_METERS = 0.3048
    METERS_TO_KM = 1000
    KM_TO_METERS = 0.001

def get_pace_display_text(pace):
    m, s = divmod(pace*60, 60)
    return (f'{m:.0f}:{int(s):02d}')

def gen_abbrev_paces(paces):
    assert len(paces) > 0
    indices = gen_critical_segments(paces)
    return paces[indices]

def gen_critical_segments(paces, eps=1e-5):
    assert len(paces) > 0
    mask = abs(np.diff(paces)) > eps
    indices = np.insert(np.where(mask)[0] + 1, 0, 0)
    return indices

def gen_elapsed_distances(paces, start_distances, total_distance):
    indices = gen_critical_segments(paces)
    critical_distances = np.append(start_distances[indices], total_distance)
    return np.diff(critical_distances)

def get_pace_adjustment_scalar(grade):
    """
    Returns amount that we change the pace in minutes / mile for a given elevation grade using
    Jack Daniels formula
    """
    if grade > 0:
        return (12 * abs(grade) / 60)
    else:
        return (-7 * abs(grade) / 60)

def get_pace_adjustments(grades):
    vf = np.vectorize(get_pace_adjustment_scalar)
    return vf(grades)

def cprint(text: str, bkd_color: str = "cyan"):
    '''
    Prints colored bkd text to terminal.

    \033[40m - Black
    \033[41m - Red
    \033[42m - Green
    \033[43m - Yellow
    \033[44m - Blue
    \033[45m - Magenta
    \033[46m - Cyan
    \033[47m - White
    '''
    print("\033[46m" + str(text) + "\033[00m")