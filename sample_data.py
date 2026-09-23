from data_generator import generate_fitness_data

# (session_id, scenario_name, seed) - scenario_name must match one of the
# names in data_generator.available_scenarios()
SCENARIOS = [
    ("Resting", "resting", 1),
    ("Moderate activity", "moderate_activity", 2),
    ("High activity", "high_activity", 3),
    ("Recovery", "recovery", 4),
    ("Poor quality data", "poor_quality", 5),
]


def build_all_scenarios():
    """
    Return a list of (session_id, participant_profile, observations) for
    all five required demo scenarios, using the instructor's generator.
    """
    scenarios = []
    for session_id, scenario_name, seed in SCENARIOS:
        profile, observations = generate_fitness_data(
            scenario=scenario_name,
            seed=seed,
            number_of_windows=10,
        )
        scenarios.append((session_id, profile, observations))
    return scenarios
