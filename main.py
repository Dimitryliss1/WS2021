import numpy as np
import pandas as pd

test = pd.DataFrame(data=np.eye(5), index=[str(i) for i in range(1, 6)], columns=[str(i) for i in range(10, 15)])

test.to_csv("TEST.csv")