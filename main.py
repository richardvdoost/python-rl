import numpy as np
import pickle

from brain import Brain
from brain.activation_functions import Identity, ReLU, Sigmoid, Softplus
from games import TicTacToe
from players import RandomPlayer, PolicyGradientPlayer
from plotter import Plotter

# Set some NumPy print options
np.set_printoptions(precision=3, suppress=True, floatmode="fixed")

# Hyper parameters
UPDATE_EVERY = 200

DISCOUNT_FACTOR = 0.5
REWARD_FACTOR = 1
TRAIN_ITERATIONS = 1
EXPERIENCE_BATCH_SIZE = 1024
EXPERIENCE_BUFFER_SIZE = 10 * EXPERIENCE_BATCH_SIZE

LEARNING_RATE = 0.2
MOMENTUM = 0.9
REGULARIZATION = 0.01

BRAIN_TOPOLOGY = (
    (18, None),
    (96, ReLU),
    (9, Sigmoid),
)

# try:
# player_brain = pickle.load(open("brain/saved/player_brain_new.pickle", "rb"))
#     pre_trained_brain = pickle.load(open("brain/saved/tictactoe_good.pickle", "rb"))
#     opponent = PolicyGradientPlayer(pre_trained_brain)
#     opponent.is_learning = False
#     print("Going to play against a pre-trained player!!")
# except Exception:
opponent = RandomPlayer()
player_brain = Brain(BRAIN_TOPOLOGY, learning_rate=LEARNING_RATE, momentum=MOMENTUM, regularization=REGULARIZATION)

policy_player = PolicyGradientPlayer(
    player_brain,
    discount_factor=DISCOUNT_FACTOR,
    reward_factor=REWARD_FACTOR,
    train_iterations=TRAIN_ITERATIONS,
    experience_batch_size=EXPERIENCE_BATCH_SIZE,
    experience_buffer_size=EXPERIENCE_BUFFER_SIZE,
)

tictactoe_game = TicTacToe((policy_player, opponent))

# Initialize plot data
game_counts = []
wins = []
losses = []
scores = []
mean_experience_values = []
brain_costs = []
brain_costs_ema = []
weight_ranges = []

# Create a plot figure
plot_data = {
    "score": {
        "placement": 221,
        "graphs": [
            {"label": "Score", "color": "blue"},
            {"label": "% Losses", "color": "red"},
            {"label": "% Wins", "color": "green"},
        ],
        "ylabel": f"Average of {UPDATE_EVERY} Games",
        "legend": True,
    },
    "value": {"placement": 222, "graphs": [{"color": "blue"}], "ylabel": f"Mean Experience Value"},
    "cost": {
        "placement": 223,
        "graphs": [{"color": "red_transp"}, {"color": "red"}],
        "ylabel": f"Brain Cost of Last Batch",
        "xlabel": f"Games Played",
    },
    "weights": {
        "placement": 224,
        "graphs": [{"color": "blue"}],
        "ylabel": f"Weights Range",
        "xlabel": f"Games Played",
    },
}
plotter = Plotter("Policy Network Performance", plot_data)

game_count = 0
prev_score = None
prev_mean_experience_value = None
brain_cost_ema = None
perfect_score_count = 0
running = True
while running:
    try:
        tictactoe_game.play(UPDATE_EVERY)
        game_count += UPDATE_EVERY

        score_tuple = tictactoe_game.score
        score_tuple_rel = score_tuple[0] / UPDATE_EVERY * 100, score_tuple[1] / UPDATE_EVERY * 100
        score = score_tuple_rel[0] - score_tuple_rel[1]
        score_diff = (score - prev_score) / abs(prev_score) * 100 if prev_score else 0
        prev_score = score

        mean_experience_value = policy_player.mean_experience_value
        mean_experience_value_diff = (
            (mean_experience_value - prev_mean_experience_value) / abs(prev_mean_experience_value) * 100
            if prev_mean_experience_value
            else 0.0
        )
        prev_mean_experience_value = mean_experience_value

        brain_cost = player_brain.cost
        brain_cost_ema = (
            0.9 * brain_cost_ema + 0.1 * brain_cost if brain_cost_ema and not np.isnan(brain_cost_ema) else brain_cost
        )

        weight_range = player_brain.weight_range

        # Useful info
        print(
            f"Games Played: {game_count}\n"
            f"Score: {score:5.1f}% {score_diff:+4.1f}%\n"
            f"Wins / Losses: {score_tuple_rel[0]:.1f}% / {score_tuple_rel[1]:.1f}%\n"
            f"Mean Experience Value: {mean_experience_value:6.3f} {mean_experience_value_diff:+4.1f}%\n"
            f"Experience Buffer Usage: {policy_player.experience_buffer_usage * 100:5.1f}%\n"
            f"Brain Cost: {brain_cost:4.3f}\n"
            f"Brain Cost EMA: {brain_cost_ema:4.3f}\n"
            f"Weight Range: [{weight_range[0]:6.3f}, {weight_range[1]:6.3f}]\n"
            f"Output: {player_brain.output[0,:]}\n"
            f"Target: {player_brain.target[0,:]}\n"
        )

        # Update plot data
        game_counts.append(game_count)
        wins.append(score_tuple_rel[0])
        losses.append(score_tuple_rel[1])
        scores.append(score)
        mean_experience_values.append(mean_experience_value)
        brain_costs.append(brain_cost)
        brain_costs_ema.append(brain_cost_ema)
        weight_ranges.append(weight_range[1] - weight_range[0])
        plotter.update_data(
            {
                "score": (scores, losses, wins, game_counts),
                "value": (mean_experience_values, game_counts),
                "cost": (brain_costs, brain_costs_ema, game_counts),
                "weights": (weight_ranges, game_counts),
            }
        )

        # Stop when we have a perfect score (0 losses)
        if score_tuple[1] == 0:
            print(f"Played perfectly for {UPDATE_EVERY} games in a row 😬 Stopping")

            # Save the trained brain, and the plots
            settings_str = (
                f"-discount_fac={DISCOUNT_FACTOR}"
                f"-reward_factor={REWARD_FACTOR}"
                f"-train_iterations={TRAIN_ITERATIONS}"
                f"-experience_batch_size={EXPERIENCE_BATCH_SIZE}"
                f"-experience_buffer_size={EXPERIENCE_BUFFER_SIZE}"
                f"-learning_rate={LEARNING_RATE}"
                f"-momentum={MOMENTUM}"
                f"-regularization={REGULARIZATION}"
            )
            for hidden_layer in BRAIN_TOPOLOGY[1:-1]:
                settings_str += f"hl-neurons={hidden_layer[0]}{hidden_layer[1].__name__}"
            pickle.dump(player_brain, open(f"brain/saved/player_brain{settings_str}.pickle", "wb"))
            plotter.save_image(f"plots/performance-plot{settings_str}.png")

            running = False

        tictactoe_game.reset_score()

    except KeyboardInterrupt:
        running = False

plotter.save_image(f"plots/performance-plot.png")
