import argparse
import sys
import numpy as np

import gym
from gym import wrappers, logger
import tensorflow as tf

sys.path.insert(0,'./baselines/')
#print(sys.path)
from baselines.ppo2.model import Model
from baselines.common.policies import build_policy
from baselines.common.cmd_util import make_vec_env
from baselines.common.vec_env.vec_frame_stack import VecFrameStack
from baselines.common.vec_env.vec_normalize import VecNormalize
from baselines.common.vec_env.vec_video_recorder import VecVideoRecorder

class RandomAgent(object):
    """The world's simplest agent!"""
    def __init__(self, action_space):
        self.action_space = action_space

    def act(self, observation, reward, done):
        return self.action_space.sample()

class PPO2Agent(object):
    def __init__(self, env, env_type, stochastic):
        ob_space = env.observation_space
        ac_space = env.action_space
        self.stochastic = stochastic

        if env_type == 'atari':
            policy = build_policy(env,'cnn')
        elif env_type == 'mujoco':
            policy = build_policy(env,'mlp')

        make_model = lambda : Model(policy=policy, ob_space=ob_space, ac_space=ac_space, nbatch_act=1, nbatch_train=1,
                        nsteps=1, ent_coef=0., vf_coef=0.,
                        max_grad_norm=0.)
        self.model = make_model()

    def load(self, path):
        self.model.load(path)

    def act(self, observation, reward, done):
        if self.stochastic:
            a,v,state,neglogp = self.model.step(observation)
        else:
            a = self.model.act_model.act(observation)
        return a


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=None)
    parser.add_argument('--env_id', default='', help='Select the environment to run')
    parser.add_argument('--env_type', default='', help='mujoco or atari')
    parser.add_argument('--model_path', default='')
    parser.add_argument('--episode_count', default=100)
    parser.add_argument('--record_video', action='store_true')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--seed', default = 1234, type=int)
    parser.add_argument('--no_op', action='store_true')

    args = parser.parse_args()


    seed = int(args.seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)

    stochastic = True #it helps Atari policies to not get stuck if there is a little noise

    # You can set the level to logger.DEBUG or logger.WARN if you
    # want to change the amount of output.
    logger.set_level(logger.INFO)

    #env = gym.make(args.env_id)

    #env id, env type, num envs, and seed
    env = make_vec_env(args.env_id, args.env_type, 1, 0,
                       wrapper_kwargs={
                           'clip_rewards':False,
                           'episode_life':False,
                       })
    if args.record_video:
        env = VecVideoRecorder(env,'./videos/',lambda steps: True, 200000) # Always record every episode

    if args.env_type == 'atari':
        env = VecFrameStack(env, 4)
    elif args.env_type == 'mujoco':
        env = VecNormalize(env,ob=True,ret=False,eval=True)
    else:
        assert False, 'not supported env type'

    try:
        env.load(args.model_path) # Reload running mean & rewards if available
    except AttributeError:
        pass

    if not args.no_op:
        agent = PPO2Agent(env,args.env_type, stochastic)
        agent.load(args.model_path)
        #agent = RandomAgent(env.action_space)

    episode_count = args.episode_count
    reward = 0
    done = False

    env_test=gym.make(args.env_id)
    print(env_test.unwrapped.get_action_meanings())
    from pyvirtualdisplay import Display

    virtual_display = Display(visible=0, size=(1400, 900))
    virtual_display.start()
    for i in range(int(episode_count)):
        ob = env.reset()
        steps = 0
        acc_reward = 0
        while steps < 7000:
            if args.no_op:
                action = 0
            else:
                action = agent.act(ob, reward, done)
            #action = env.action_space.sample()
            ob, reward, done, _ = env.step(action)
            if args.render:
                env.render()

            steps += 1
            acc_reward += reward
            if done:
                print(steps,acc_reward)
                break
    env.close()
    env.venv.close()
    virtual_display.stop()
