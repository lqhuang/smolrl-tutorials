# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path

import gymnasium as gym
import numpy as np

# import random
# import string
import typer
from matplotlib import pyplot as plt
from rich.console import Console
from tqdm import tqdm

from smolrl.agents import QLearningAgent
from smolrl.envs import PlayEnum, RenderEnum, human_play
from smolrl.envs.flappy_bird import (
    ACTION_LABELS,
    FLAPPY_BIRD_SIMPLE_V1,
    FlappyBirdSimpleEnv,
    FlappyBirdSimpleParams,
    wait_human_input,
)

console = Console()


@dataclass
class TraningParams:
    total_episodes: int  # Total episodes
    learning_rate: float  # Learning rate
    gamma: float  # Discounting rate
    epsilon: float  # Exploration probability
    n_runs: int  # Number of runs
    savefig_folder: Path  # Root folder where plots are saved


def init_env(params: FlappyBirdSimpleParams) -> FlappyBirdSimpleEnv:
    env = gym.make(FLAPPY_BIRD_SIMPLE_V1, **asdict(params))
    action_size = env.action_space.n
    console.print("Environment initialized ...")
    console.print(f"Action size: {action_size}")
    return env  # type: ignore


def run_experiments(env: FlappyBirdSimpleEnv, params: TraningParams):
    rewards = np.zeros((params.total_episodes, params.n_runs))
    steps = np.zeros((params.total_episodes, params.n_runs))
    episodes = np.arange(params.total_episodes)
    qtables = np.zeros((params.n_runs, env.action_space.n))
    all_states = []
    all_actions = []

    agent = QLearningAgent(
        learning_rate=params.learning_rate,
        gamma=params.gamma,
        epsilon=params.epsilon,
        state_space=env.observation_space,
        action_space=env.action_space,
    )
    console.print("Agent initialized ...")

    for run in range(params.n_runs):  # Run several times to account for stochasticity
        agent.reset()

        for episode in tqdm(
            episodes, desc=f"Run {run}/{params.n_runs} - Episodes", leave=False
        ):
            # init
            state = env.reset()[0]
            step = 0
            done = False
            total_rewards = 0.0

            # training
            while not done:
                # action = env.action_space.sample()
                action = agent.choose_action(state)

                # Log all states and actions
                all_states.append(state)
                all_actions.append(action)

                # Take the action (a) and observe the outcome state(s') and reward (r)
                new_state, reward, terminated, truncated, info = env.step(action)

                agent.update(state, action, reward, new_state)

                done = terminated or truncated
                total_rewards += reward  # pyright: ignore[reportOperatorIssue]
                step += 1

                if done:
                    state = env.reset()[0]
                else:
                    state = new_state

            # Log all rewards and steps
            rewards[episode, run] = total_rewards
            steps[episode, run] = step

    return rewards, steps, episodes, qtables, all_states, all_actions


def main(
    play_mode: PlayEnum = typer.Option(
        PlayEnum.human, show_choices=True, help="Run mode: `human` or `agent`"
    ),
    render_mode: RenderEnum = typer.Option(  # type: ignore[assignment]
        RenderEnum.human, help="Render mode: `human`or `rgb_array`"
    ),
    expname: str | None = None,
):
    exp_dirname = expname or int(time.monotonic())
    env_params = FlappyBirdSimpleParams(render_mode=render_mode.value, pipe_gap=300)
    train_params = TraningParams(
        total_episodes=2000,
        learning_rate=0.8,
        gamma=0.95,
        epsilon=0.1,
        n_runs=20,
        savefig_folder=Path(f"./run/{exp_dirname}"),
    )

    env = init_env(env_params)

    if play_mode == PlayEnum.human:
        human_play(env, wait_human_input)
        env.close()
        return

    rewards, steps, episodes, qtables, all_states, all_actions = run_experiments(
        env, train_params
    )
    env.close()
    train_params.savefig_folder.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    typer.run(main)
