# %%
import gistim
import os

# %%

os.chdir("c:/tmp/timtests")
gistim.compute_steady(path="test3.json")

# %%

import numpy as np
import timml

# %%


t_0 = 0.0
t_1 = 10.0
s_l = 0.7
s_u = 0.3
f_amp = 1.25

s_scaled = (f_amp - 1.0) * (t_1 - t_0)
L_sto = (s_scaled + s_l + s_u) / 2
# %%

count_L = np.round(np.log(L_sto / s_l) / np.log(f_amp))
count_U = np.round(np.log(L_sto / s_u) / np.log(f_amp))
# %%
count_L = max(np.round(count_L).astype(int) , 0)
count_U = max(np.round(count_U).astype(int) , 0)
# %%

L_lower = f_amp ** (-count_L)
L_upper = f_amp ** (-count_U)
# %%
L_sto2 = s_scaled / (2 - L_lower - L_upper)
# %%

L_lower = L_lower * L_sto2
L_upper = L_upper * L_sto2
# %%

lower_dt = L_lower * (f_amp ** np.arange(count_L))
upper_dt = L_upper * (f_amp ** np.arange(count_U))[::-1]
# %%
