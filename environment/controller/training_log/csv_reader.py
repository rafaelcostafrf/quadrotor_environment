import pandas as pd
import numpy as np
import glob 

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("pgf")
matplotlib.rcParams.update({
    "pgf.texsystem": "pdflatex",
    'font.family': 'serif',
    'text.usetex': True,
    'pgf.rcfonts': False,
    'pgf.preamble':[
        '\DeclareUnicodeCharacter{2212}{-}']
})

header = ['Total Time', 'Solved Avg', 'Reward Avg', 'Sim Time', 'Total Episodes', 'Sim Time/Ep']
avg_df = pd.DataFrame(columns = header)
neural_sizes = [16, 32, 64, 128, 256]
fig, axs = plt.subplots(len(neural_sizes), figsize = (7, 7*1.414))

for k, N in enumerate(neural_sizes):
    df_array = []
    if N < 128:
        name = 'log_0'+str(N)
    else:
        name = 'log_'+str(N)
        
    for file in glob.glob(name+'*.csv'):
        df_array.append(pd.read_csv(file))
    
    reward_array = np.zeros([400, 4])
    time_array = np.zeros([400, 4])
    solved_array = np.zeros([400, 4])
    timesteps_array = np.zeros([400, 4])
    episodes_array = np.zeros([400, 4])
    for i, df in enumerate(df_array):
        reward = df['Avg_reward'].to_numpy()
        time = df['T_seconds'].to_numpy()
        solved = df['Solved Avg'].to_numpy()
        timesteps = df['Total Timesteps'].to_numpy()
        episodes = df['Total Episodes'].to_numpy()
        reward_array[:, i] = reward
        time_array[:, i] = time
        solved_array[:, i] = solved
        timesteps_array[:, i] = timesteps
        episodes_array[:, i] = episodes
    
    d =[np.mean(time_array[-1, :])/3600, np.mean(solved_array[-20, :]), np.mean(reward_array[-20, :]), np.mean(timesteps_array[-1, :])*0.01/3600, np.mean(episodes_array[-1, :]), np.mean(timesteps_array[-1, :])*0.01/np.mean(episodes_array[-1, :])]
    
    log = pd.Series(data = d, name = str(N), index = header)
    
    avg_df = avg_df.append(log)
    
    mean_reward = np.mean(reward_array, axis = 1)
    std_reward = np.std(reward_array, axis = 1)
    
    
    x = np.arange(400)*5
    # axs[k].set_title(name)
    axs[k].plot(x, mean_reward, label ='N: '+str(N))
    axs[k].fill_between(x, mean_reward-std_reward, mean_reward+std_reward, alpha = 0.5)
    axs[k].grid(True)
    axs[k].legend()
fig.text(0.5, 0.08, 'Ep. Treinamento', ha='center')
fig.text(0.06, 0.5, 'Recompensa', va='center', rotation='vertical')    
# plt.show()
plt.savefig('N.pgf',bbox_inches='tight')
print(avg_df)