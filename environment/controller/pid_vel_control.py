import numpy as np
import pandas as pd
import sys
import os
os.chdir('/home/rafaelcostaf/mestrado/quadrotor_environment/')
# sys.path.append()
from environment.quadrotor_env import quad, plotter
from environment.quaternion_euler_utility import euler_quat, quat_euler
from environment.controller.response_analyzer import response_analyzer
from environment.controller.target_parser import target_parse, episode_n
from mission_control.mission_control import mission
import matplotlib.pyplot as plt


seed = 1

clipped = True
if  clipped:
    P, I, D = 1, -0.0, 0
    P_z, I_z, D_z = 0.4, -0.0, 0
    P_a, I_a, D_a = 20, 0, 20
    P_ps, I_ps, D_ps =  5, 0, 5
else:
    P, I, D = 2, -0.0, 0
    P_z, I_z, D_z = 1, -0.0, 0
    P_a, I_a, D_a = 180, 0, 50
    P_ps, I_ps, D_ps =  40, 0, 20

class pid_control():
    def __init__(self, drone_env):
        self.env = drone_env
        self.pid_x = pid(P, I, D) 
        self.pid_y = pid(P, I, D) 
        self.pid_z = pid(P_z, I_z, D_z) 
        
        self.pid_phi = pid(P_a, I_a, D_a) 
        self.pid_theta = pid(P_a, I_a, D_a) 
        self.pid_psi = pid(P_ps, I_ps, D_ps) 
        
        self.ang_d_ant = np.zeros(3)
        
        self.log_state = []
        self.log_input = []
        self.log_target = []
        
        self.att_target = []
        
    def lower_control(self, xd, dxd):
        
        # [x, y, z] = self.env.state[0:5:2]
        [dx, dy, dz] = self.env.state[1:6:2]
        [ax, ay, az] = self.env.accel.flatten()
        
        u_1 = self.pid_x.pid(dx, 0, xd[0], 0)
        u_2 = self.pid_y.pid(dy, 0, xd[1], 0)
        u_3 = self.pid_z.pid(dz, 0, xd[2], 0)

        theta_d = np.arctan2(u_1, (u_3+self.env.gravity))
        
        phi_d = np.arctan2(-u_2*np.cos(theta_d), (u_3+self.env.gravity))
        
        U_1 = self.env.mass*(u_3 + self.env.gravity)/(np.cos(theta_d)*np.cos(phi_d))
        
        return U_1, phi_d, theta_d
        
        
    def upper_control(self, ang_d, v_ang_d):
        [phi, theta, psi] = self.env.ang
        [dp, dt, dps] = self.env.ang_vel
        
        u_5 = self.pid_phi.pid(phi, dp, ang_d[0], v_ang_d[0])
        u_6 = self.pid_theta.pid(theta, dt, ang_d[1], v_ang_d[1])
        u_7 = self.pid_psi.pid(psi, dps, ang_d[2], v_ang_d[2])

        sp = np.sin(phi)
        cp = np.cos(phi)

        st = np.sin(theta)
        ct = np.cos(theta)
        tt = np.tan(theta)

        b_1 = 1/self.env.J_mat[0, 0]
        b_2 = tt*sp/self.env.J_mat[1, 1]
        b_3 = tt*cp/self.env.J_mat[2, 2]
        b_4 = cp/self.env.J_mat[1, 1]
        b_5 = -sp/self.env.J_mat[2, 2]
        b_6 = sp/ct/self.env.J_mat[1, 1]
        b_7 = cp/ct/self.env.J_mat[2, 2]

        M = np.array([[b_1, b_2, b_3], 
                      [0, b_4, b_5],
                      [0, b_6, b_7]])

        [U_2, U_3, U_4] = np.dot(np.linalg.inv(M), np.array([[u_5, u_6, u_7]]).T).flatten()

        return U_2, U_3, U_4
    
    def control(self, xd , dxd , psd , dpsd ):
            
        self.error_mission = np.array([xd[0], dxd[0], xd[1], dxd[1], xd[2], dxd[2], psd, dpsd])
        
        F_Z, phi_d, theta_d = self.lower_control(xd, dxd)
        self.att_target.append([phi_d, theta_d])
        ang_d = np.array([phi_d, theta_d, psd])
        v_ang_d = (ang_d - self.ang_d_ant)/drone.t_step
        [M_X, M_Y, M_Z] = self.upper_control(ang_d, v_ang_d)
        self.ang_d_ant = ang_d
        action = np.array([F_Z, M_X, M_Y, M_Z])
        
        return action
    
   
class pid():
    def __init__(self, P, I, D, timestep=0.01):
        self.ix = 0
        self.p = P
        self.i = I
        self.d = D
        self.ts = timestep
        self.x_old = 0
        
    def pid(self, x, dx, x_d, dx_d=0):
        dx = (x - self.x_old)/self.ts
        self.x_old = x
        self.ix = self.ix+(x_d-x)*self.ts
        control = self.p*(x_d-x)+self.d*(dx_d-dx)-self.i*(self.ix)
        return control


mission_total_time = 500
total_episodes = 20
drone = quad(0.01, mission_total_time, training = True, euler=0, direct_control=0, T=5, clipped = clipped)
drone.seed(seed)
initial_state = np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0])
effort_array = []
solved = 0
plot = plotter(drone, True, False)

memory_array = np.zeros([total_episodes, mission_total_time, 13])

for i in range(total_episodes):
# state, action = drone.reset(initial_state)
    state, action = drone.reset()
    controller = pid_control(drone)
    action = np.array([9.82*1.03, 0, 0, 0])

    j = 0
    effort = 0
    while j < mission_total_time:

        state, _, _ = drone.step(action)
        X = np.array([0, 0, 0])
        z = np.zeros(3)
        
        action = controller.control(X, z, 0, 0)
        target = np.array([0, X[0], 0, X[1], 0, X[2], 1, 0, 0, 0, 0, 0, 0, 0])
        plot.add(target)
        effort += np.sum(np.abs(drone.step_effort))
        
        memory_step = np.concatenate((drone.state[1:6:2], drone.ang, drone.ang_vel, drone.step_effort))
        memory_array[i, j, :] = memory_step
        j += 1
        # print(state)
    plot.plot()    
    att = np.array(controller.att_target)
    
    plot.axs[1].plot(np.arange(j)/100, att[:,0])
    plot.axs[1].plot(np.arange(j)/100, att[:,1])
    # plt.plot(np.arange(j), att[:,1])
    plt.show()
    
clipped_str = '' if clipped else '_not_clipped'
np.save('./environment/controller/classical_controller_results/pid_log_same_start'+clipped_str, memory_array)