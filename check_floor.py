import numpy as np, h5py, pandas as pd
from policyengine_uk import Microsimulation
import os
# Prints survey-household counts behind each published cell (stdout only;
# never commit the counts).
DS=os.environ.get("MICROCOSM_DATASET","data/releases/microcosm-uk-2024-25-national/uk-frs-calibration-attempt-20261115T104657Z-fcfac709/microcosm_uk_2024_25.h5")
hh=pd.read_hdf(DS,"household")
print([c for c in hh.columns if "source" in c or c=="household_id"])
sim=Microsimulation(dataset=DS)
c=lambda v: np.asarray(sim.calculate(v,2026,map_to="household").values)
hid=c("household_id").astype(int); src=hh.set_index("household_id").loc[hid,"source_household_id"].values
gb=c("country").astype(str)!="NORTHERN_IRELAND"; dec=c("household_income_decile").astype(int)
e=c("electricity_consumption"); g=c("gas_consumption"); net=c("hbai_household_net_income")
cells={"gb":gb,"dual":gb&(e>0)&(g>0),"elec_only":gb&(e>0)&(g==0),"nonpos_income":gb&(net<=0)}
for d in range(1,11): cells[f"decile{d}"]=gb&(dec==d)
for k,m in cells.items(): print(k, "rows",int(m.sum()),"survey_hh",len(set(src[m])))
