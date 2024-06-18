import numpy as np
import pandas as pd

class MPCVariableManager():
    def __init__(self):
        self.h_hist = []
        self.w_hist = []
        self.Qout_hist = []
        self.E_hist = []
        self.P_hist = []
        self.Qin_hist = []
    
    #set to polars 
    def initialize(self, df, zs):
        # Extract initial conditions from the DataFrame
        self.h_hist = df["level"][0:zs].values
        self.w_hist = np.vstack([
            df["pump1_speed"][0:zs].values,
            df["pump3_speed"][0:zs].values,
            df["pump4_speed"][0:zs].values
        ]).reshape(3, -1)
        
        self.Qout_hist = df["outflow"][0:zs].values
        
        self.E_hist = np.vstack([
            df["pump1_power_est"][0:zs].values,
            df["pump3_power_est"][0:zs].values,
            df["pump4_power_est"][0:zs].values
        ]).reshape(3, -1)
        
        self.P_hist = df["pressure"][0:zs].values
        self.Qin_hist = df["inflow"][0:zs].values

    def update(self, sol_w,sol_Qout,sol_h,sol_E,sol_P):
        sol_w_filtered =  np.where(np.array(sol_w[:, 3]).reshape(3, 1) < 1, 0, np.array(sol_w[:, 3]).reshape(3, 1))
        self.w_hist = np.hstack(( self.w_hist, sol_w_filtered.reshape(3, 1)))
        sol_E_filtered = np.where(np.array(sol_E[:, 3]).reshape(3, 1) < 1, 0, np.array(sol_E[:, 3]).reshape(3, 1))
        self.E_hist = np.hstack(( self.E_hist, sol_E_filtered.reshape(3, 1)))
        self.Qout_hist = np.hstack((self.Qout_hist, np.array(sol_Qout[3])[0]))
        self.h_hist = np.hstack((self.h_hist, np.array(sol_h[3])[0]))
        self.P_hist = np.hstack((self.P_hist, np.array(sol_P[3])[0]))
        
    def create_results_dataframe(self):
        sol_dict = {"w1": self.w_hist[0], 
            "w2": self.w_hist[1],
            "w3": self.w_hist[2],
            "Qout": self.Qout_hist,
            "h": self.h_hist,
            "P": self.P_hist,
            "E1": self.E_hist[0],
            "E2": self.E_hist[1],
            "E3": self.E_hist[2]}
        print("Dataframe created!")
        return pd.DataFrame(sol_dict)
        


