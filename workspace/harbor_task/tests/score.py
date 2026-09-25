import math

def score(accuracy,baseline):
    if not all(math.isfinite(x) for x in (accuracy,baseline)) or not (0<=accuracy<=1 and 0<=baseline<1):
        raise ValueError('Invalid accuracy/anchor')
    return (accuracy-baseline)/(1-baseline)
