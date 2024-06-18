import casadi as ca
import numpy as np


def setup_OptiProblem(N,zs,Ts)->ca.Function:
    # Create an Opti instance
    opti = ca.Opti()

    # Solver options
    p_opts = {
        #"qpsol": "qrqp",
        #"convexify_strategy": "regularize",
        "expand":False,
        "print_time": 0,
        "verbose": False,
        "error_on_fail": False,
        
    }
    opti.solver("ipopt",p_opts)

    # #============= Tank Model ==================
    A = 18

    # #=========== Parameters of the static models
    B1_pressure = np.array([9.2727E-05])
    B2_pressure = np.array([2.5979E-08])
    C_pressure = np.array([5.3955E-01])



    #=========== Parameters of the ARX model
    # array of params
    A_power = np.hstack([np.diag([1.6108E-01, 3.6872E-03, 2.3590E-01]), np.diag([9.5030E-02, 3.1648E-03, 1.9355E-01])])
    B_power = np.diag([3.5117E-02, 4.1216E-02, 2.7095E-02])
    C_power = np.array([0, 0, 1.5144E-03]).reshape((3,-1))

    #=========== Desired value of y 
    Qout_meas = opti.parameter(zs)   # ascending index: older data, at 0: last measured value (t-1)
    Qin_est = opti.parameter(N+zs)
    h_ref = opti.parameter(N+zs)
    w_meas =  opti.parameter(3,zs)
    h_meas = opti.parameter(zs)
    E_meas = opti.parameter(3,zs)
    P_meas = opti.parameter(zs)

    trigger = opti.parameter(3) # Trigger constant over entire horizon

    #=========== Declare Symbolic Variables
    Qout = 100*opti.variable(N+zs)
    E = opti.variable(3,N+zs)
    P = opti.variable(N+zs)
    w = 150*opti.variable(3,N+zs)
    h = opti.variable(N+zs)
    effi = opti.variable(N+zs)

    #============= Slack Variables
    s_h = opti.variable(N+zs)
    s_P = opti.variable(N+zs)


    #=========== Objective function
    objective = 0

    for t in range(3, N+zs):
        objective += 0.05*(E[:,t].T @ E[:,t]) + 10*(h[t]-h_ref[t])**2  + 0.5*((w[:,t]-w[:,t-1]).T @ (w[:,t]-w[:,t-1]))+1000*s_P[t]**2 + 1000*s_h[t]**2 + 0.5*(ca.if_else(trigger[0] > 0, 0,w[0,t]) + ca.if_else(trigger[1] > 0, 0,w[1,t]) +ca.if_else(trigger[2] > 0, 0,w[2,t]))

    opti.minimize(objective)   


    # ARX model constraints
    for t in range(zs, N+zs):

        # # Qout_next,E_next,P_next,h_next = system_dynamics(w[:,t-zs:],Qout[t-zs:],Qin_est[t-zs:],P[t-zs:],E[:,t-zs:],h[t-zs:],Ts)
        # Qout_next,E_next,P_next,h_next = system_dynamics(w,Qout,Qin_est,P,E,h,Ts)
        # opti.subject_to(Qout[t] == Qout_next)
        # opti.subject_to(E[:,t] == E_next)
        # opti.subject_to(P[t] == P_next)
        # opti.subject_to(h[t] == h_next)
        opti.subject_to(Qout[t] ==ca.if_else( 
                                    w[0,t-1] <= 600,
                                    3.2216 + 0.08378681 * w[0,t-1],  # First segment equation
                                    3.22 + 0.083 * 600 + 0.8371 * (w[0,t-1] - 600),  # Second segment equation, ensuring continuity at the breakpoint
                                    True) 
                                + ca.if_else(
                                    w[1,t-1] <= 600,
                                    3.2216 + 0.08378681 * w[1,t-1],  # First segment equation
                                    3.22 + 0.083 * 600 + 0.8371 * (w[1,t-1] - 600),  # Second segment equation, ensuring continuity at the breakpoint
                                    True)
                                + ca.if_else(
                                    w[2,t-1] <= 600,
                                    3.2216 + 0.08378681 * w[2,t-1],  # First segment equation
                                    3.22 + 0.083 * 600 + 0.8371 * (w[2,t-1] - 600),  # Second segment equation, ensuring continuity at the breakpoint
                                    True))


        opti.subject_to(E[:,t] == A_power @ ca.vcat([E[:,t-1],E[:,t-2]]) + B_power @ w[:,t-1] + C_power)

        opti.subject_to(P[t] == B1_pressure @ Qout[t-1] + B2_pressure @ Qout[t-1]**2 + C_pressure) 
        
        opti.subject_to(h[t] == h[t-1] + Ts/3600*(Qin_est[t-1]-Qout[t-1])/A)

    for t in range(0, N+zs):
        opti.subject_to(effi[t] == (E[0,t]+E[1,t]+E[2,t])/(Qout[t]+0.0001))


    # Additional constraints (e.g., on control input)
    for t in range(zs, N+zs):
        opti.subject_to(w[:,t] >= 0)  # Lower bound on control input
        opti.subject_to(w[:,t] <= 1500)
        

        opti.subject_to(h[t] <= (200 + s_h[t]))
        opti.subject_to(h[t] >= (120 - s_h[t]))
        opti.subject_to(P[t] <= (1 + s_P[t]))  # upper bound on pressure
        opti.subject_to(P[t] >= (0 - s_P[t]))  # lower bound on pressure

        # Slack Variables need to be constrained to positive values
        opti.subject_to(s_h[t] >= 0)
        opti.subject_to(s_P[t] >= 0)


    # Initial conditions
    opti.subject_to(Qout[0:zs]   == Qout_meas)  # Initial value of y, read from sensor
    opti.subject_to(h[0:zs]      == h_meas)
    opti.subject_to(w[:,0:zs]    == w_meas)  
    opti.subject_to(P[0:zs]      == P_meas)
    opti.subject_to(E[:,0:zs]      == E_meas)


    # TODO: Is it possible to remove this? If ommited, exception due to undefined parameters
    opti.set_value(Qin_est,0)
    opti.set_value(Qout_meas,0)
    opti.set_value(h_meas,0)
    opti.set_value(w_meas,0) 

    opti.set_value(E_meas,0)
    opti.set_value(P_meas,0)

    opti.set_value(trigger,0) # Select enabled pumps
    opti.set_value(h_ref,0)

    inputs = [Qin_est,Qout_meas,h_meas,w_meas,E_meas,P_meas,trigger,h_ref]
    outputs = [w,Qout,h,E,P,effi]
    mpc_controller = opti.to_function("mpc_controller", inputs, outputs)
    
    return mpc_controller