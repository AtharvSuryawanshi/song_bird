import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from matplotlib import patches

'''Three layer model: only used for testing!'''
# 2D reward landscapes
def gaussian(coordinates, height, mean, spread):
    x, y = coordinates[0], coordinates[1]
    return height * np.exp(-((x-mean[0])**2 + (y-mean[1])**2)/(spread**2))

def reward_fn(coordinates):
    return gaussian(coordinates, 1, [-0.9, 0.9], 0.8) #+ gaussian(coordinates, 0.2, [-0.5, 0.2], 0.2)

def new_sigmoid(x, m=0, a=0):
    """ Returns an output between -1 and 1 """
    return (2 / (1 + np.exp(-1*(x-a)*m))) - 1

# layer sizes
HVC_SIZE = 100
BG_SIZE = 50
RA_SIZE = 100
MC_SIZE = 2
n_ra_clusters = 2
n_bg_clusters = 2

RANDOM_SEED = 42

# sigmoid layer parameters
BG_sig_slope = 5  # lesser, slower the learning # BG sigmoidal should be as less steep as possible
BG_sig_mid = 0
RA_sig_slope = 15 # RA sigmoidal should be as steep as possible
RA_sig_mid = 0
MC_sig_slope = 20 # if lesser -> more difficult to climb the hill, assymptotes before 
MC_sig_mid = 0


reward_window = 10
input = np.zeros(HVC_SIZE)
input[1] = 1

# run parameters
LR_1 = 0.1
TRIALS = 10000
BG_NOISE = 0.1

class NN:
    def __init__(self, hvc_size, bg_size, ra_size, mc_size):
        self.W_hvc_bg = np.random.uniform(-1, 1, (hvc_size, bg_size)) # changing from -1 to 1
        self.W_bg_ra = np.random.uniform(0, 1, (bg_size, ra_size)) # const from 0 to 1
        self.W_ra_mc = np.random.uniform(0, 1, (ra_size, mc_size)) # const from 0 to 1

        # channel from ra to mc
        for i in range(n_ra_clusters):
            segPath = np.diag(np.ones(n_ra_clusters, int))[i]
            self.W_ra_mc[i*RA_SIZE//n_ra_clusters : (i+1)*RA_SIZE//n_ra_clusters] *= segPath
            
        # channel from bg to ra
        for i in range(n_bg_clusters):
            segPath = np.diag(np.ones(n_bg_clusters, int))[i]
            print(segPath)
            self.W_bg_ra[i*BG_SIZE//n_bg_clusters : (i+1)*BG_SIZE//n_bg_clusters] *= [j for j in segPath for r in range(RA_SIZE//n_ra_clusters)]

        self.hvc_size = hvc_size
        self.bg_size = bg_size
        self.ra_size = ra_size
        self.mc_size = mc_size
        self.ra_cluster_size = ra_size // n_ra_clusters
        
    def forward(self, input):
        self.hvc = input
        self.bg = new_sigmoid(np.dot(self.hvc, self.W_hvc_bg) + np.random.normal(0, BG_NOISE, self.bg_size) , m = BG_sig_slope, a = BG_sig_mid)
        self.ra = new_sigmoid(np.dot(self.bg/self.bg_size, self.W_bg_ra), m = RA_sig_slope, a = RA_sig_mid) 
        self.mc = new_sigmoid(np.dot(self.W_ra_mc.T, self.ra)/self.ra_cluster_size, m = MC_sig_slope, a = MC_sig_mid)
        return self.mc
class Environment:
    def __init__(self, hvc_size, bg_size, ra_size, mc_size):
        self.hvc_size = hvc_size
        self.bg_size = bg_size
        self.ra_size = ra_size
        self.mc_size = mc_size
        self.model = NN(hvc_size, bg_size, ra_size, mc_size)
        self.rewards = []
        self.actions = []
        
    def get_reward(self, action):
        return reward_fn(action)
    
    def run(self, iterations, learning_rate, input):
        for iter in tqdm(range(iterations)):
            action = self.model.forward(input)
            reward = self.get_reward(action)
            self.rewards.append(reward)
            self.actions.append(action)
            reward_baseline = np.mean(self.rewards[-reward_window:])
            self.model.W_hvc_bg += learning_rate * (reward - reward_baseline) * input.reshape(self.hvc_size, 1) * self.model.bg
            if iter % (TRIALS/10) == 0:    
                tqdm.write(f'Iteration: {iter}, Action: {action}, Reward: {reward}, Reward Baseline: {reward_baseline}')     
        
    def plot_results_and_trajectory(self):
        # plt.style.use('dark_background')
        fig, axs = plt.subplots(1, 2, figsize=(12, 6))
        
        # Plot rewards
        axs[0].plot(self.rewards)
        axs[0].set_ylim(0, 1)
        axs[0].set_xlabel('Iterations')
        axs[0].set_ylabel('Reward')
        axs[0].set_title('Reward vs Iterations')

        # Plot trajectory
        x, y = np.linspace(-2, 2, 50), np.linspace(-2, 2, 50)
        X, Y = np.meshgrid(x, y)
        Z = reward_fn([X, Y])
        contour = axs[1].contour(X, Y, Z, levels=10)
        fig.colorbar(contour, ax=axs[1], label='Reward')
        x_traj, y_traj = zip(*self.actions)
        axs[1].plot(x_traj[::20], y_traj[::20], '-b', label='Agent Trajectory', lw = 0.5, alpha = 0.5) # Plot every 20th point for efficiency
        axs[1].scatter(x_traj[0], y_traj[0], c='b', label='Starting Point')  # Plot first point as red circle
        axs[1].scatter(x_traj[-1], y_traj[-1], c='r', label='Ending Point')
        # Plot square
        square = patches.Rectangle((-1, -1), 2, 2, linewidth=1, edgecolor='r', facecolor='none')
        axs[1].add_patch(square)
        axs[1].set_title('Contour plot of reward function')
        axs[1].set_xlabel('x')
        axs[1].set_ylabel('y')
        axs[1].legend()
        plt.tight_layout()
        plt.show()
    
np.random.seed(RANDOM_SEED)
env = Environment(HVC_SIZE, BG_SIZE, RA_SIZE, MC_SIZE)
env.run(TRIALS, LR_1, input)
env.plot_results_and_trajectory()