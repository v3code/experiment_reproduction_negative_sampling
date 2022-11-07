"""Simple random agent.

Running this script directly executes the random agent in environment and stores
experience in a replay buffer.
"""

# Get env directory
import sys
from pathlib import Path
if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

import argparse

# noinspection PyUnresolvedReferences
import ns.envs as envs

import ns.utils as utils

import gym
from gym import logger

import numpy as np
from PIL import Image


class RandomAgent(object):
    """The world's simplest agent!"""

    def __init__(self, action_space, no_immovable_actions=False):
        self.action_space = action_space
        self.no_immovable_actions = no_immovable_actions

    def act(self, observation, reward, done):
        del observation, reward, done

        if self.no_immovable_actions:
            tmp_action = self.action_space.sample()
            while tmp_action < 8:
                tmp_action = self.action_space.sample()
            return tmp_action
        else:
            return self.action_space.sample()


def crop_normalize(img, crop_ratio):
    img = img[crop_ratio[0]:crop_ratio[1]]
    img = Image.fromarray(img).resize((50, 50), Image.ANTIALIAS)
    return np.transpose(np.array(img), (2, 0, 1)) / 255


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=None)
    parser.add_argument('--env_id', type=str, default='ShapesTrain-v0',
                        help='Select the environment to run.')
    parser.add_argument('--fname', type=str, default='data/shapes_train.h5',
                        help='Save path for replay buffer.')
    parser.add_argument('--num_episodes', type=int, default=1000,
                        help='Total number of episodes to simulate.')
    parser.add_argument('--atari', action='store_true', default=False,
                        help='Run atari mode (stack multiple frames).')
    parser.add_argument('--no-immovable-actions', action='store_true', default=False)
    parser.add_argument('--save-state-ids', action='store_true', default=False)
    parser.add_argument('--seed', type=int, default=1,
                        help='Random seed.')
    parser.add_argument('--steps', type=int, default=50,
                        help='Random seed.')
    args = parser.parse_args()

    logger.set_level(logger.INFO)

    env = gym.make(args.env_id)

    np.random.seed(args.seed)
    env.action_space.seed(args.seed)
    env.seed(args.seed)

    agent = RandomAgent(env.action_space, no_immovable_actions=args.no_immovable_actions)

    episode_count = args.num_episodes
    reward = 0
    done = False

    crop = None
    warmstart = None
    if args.env_id == 'PongDeterministic-v4':
        crop = (35, 190)
        warmstart = 58
    elif args.env_id == 'SpaceInvadersDeterministic-v4':
        crop = (30, 200)
        warmstart = 50

    if args.atari:
        env._max_episode_steps = warmstart + args.steps + 1

    replay_buffer = []

    for i in range(episode_count):

        if args.save_state_ids:
            replay_buffer.append({
                'obs': [],
                'action': [],
                'next_obs': [],
                'state_ids': [],
                'next_state_ids': []
            })
        else:
            replay_buffer.append({
                'obs': [],
                'action': [],
                'next_obs': [],
            })

        ob = env.reset()

        if args.atari:

            # Burn-in steps
            for _ in range(warmstart):
                action = agent.act(ob, reward, done)
                ob, _, _, _ = env.step(action)
            prev_ob = crop_normalize(ob, crop)
            ob, _, _, _ = env.step(0)
            ob = crop_normalize(ob, crop)

            while True:
                replay_buffer[i]['obs'].append(
                    np.concatenate((ob, prev_ob), axis=0))
                prev_ob = ob

                if args.save_state_ids:
                    replay_buffer[i]['state_ids'].append(np.array(env.unwrapped._get_ram(), dtype=np.int32))

                action = agent.act(ob, reward, done)
                ob, reward, done, _ = env.step(action)
                ob = crop_normalize(ob, crop)

                if args.save_state_ids:
                    replay_buffer[i]['next_state_ids'].append(np.array(env.unwrapped._get_ram(), dtype=np.int32))

                replay_buffer[i]['action'].append(action)
                replay_buffer[i]['next_obs'].append(
                    np.concatenate((ob, prev_ob), axis=0))

                if done:
                    break
        else:

            while True:
                replay_buffer[i]['obs'].append(ob[1])

                if args.save_state_ids:
                    replay_buffer[i]['state_ids'].append(env.env.get_state_id())

                action = agent.act(ob, reward, done)
                ob, reward, done, _ = env.step(action)

                if args.save_state_ids:
                    replay_buffer[i]['next_state_ids'].append(env.env.get_state_id())

                replay_buffer[i]['action'].append(action)
                replay_buffer[i]['next_obs'].append(ob[1])

                if done:
                    break

        if i % 10 == 0:
            print("iter "+str(i))

    env.close()

    # Save replay buffer to disk.
    utils.save_list_dict_h5py(replay_buffer, args.fname)

