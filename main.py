REQUIRED_FIELDS = [
    "timestamp",
    "heart_rate",
    "skin_response",
    "temperature",
    "activity_level",
    "signal_quality",
]

MIN_SIGNAL_QUALITY = 0.5    # readings below this are treated as too noisy to trust
MIN_VALID_OBSERVATIONS = 3  # minimum usable readings needed to analyze a session


def validate_observation(data):
    """
    Checks one measurement for missing or impossible values, or
    bad signal quality. Returns (is_valid, reason), so we know
    why it failed.
    """
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            return False, f"missing field '{field}'"

    heart_rate = data["heart_rate"]
    if not (30 <= heart_rate <= 220):
        return False, f"impossible heart rate ({heart_rate})"

    temperature = data["temperature"]
    if not (25.0 <= temperature <= 45.0):
        return False, f"impossible skin temperature ({temperature})"

    activity_level = data["activity_level"]
    if not (0.0 <= activity_level <= 1.0):
        return False, f"activity level out of range ({activity_level})"

    skin_response = data["skin_response"]
    if skin_response < 0:
        return False, f"negative skin response ({skin_response})"

    signal_quality = data["signal_quality"]
    if not (0.0 <= signal_quality <= 1.0):
        return False, f"signal quality out of range ({signal_quality})"
    if signal_quality < MIN_SIGNAL_QUALITY:
        return False, f"signal quality too poor ({signal_quality})"

    return True, "ok"


def calculate_average(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def calculate_min_max(values):
    if not values:
        return 0.0, 0.0
    return min(values), max(values)


def detect_recovery(heart_rates, activity_levels):

    """
    Checks if heart rate and activity go down near the end, compared to peak.
    """
    total_measurements = len(heart_rates)
    if total_measurements < 4:
        return False

    end_measure_count = max(1, total_measurements // 3)
    split_index = total_measurements - end_measure_count

    early_heart_rates = []
    late_heart_rates = []
    early_activity_levels = []
    late_activity_levels = []
    for i in range(total_measurements):
        if i < split_index:
            early_heart_rates.append(heart_rates[i])
            early_activity_levels.append(activity_levels[i])
        else:
            late_heart_rates.append(heart_rates[i])
            late_activity_levels.append(activity_levels[i])

    peak_heart_rate = max(early_heart_rates)
    peak_activity_level = max(early_activity_levels)
    avg_late_heart_rate = calculate_average(late_heart_rates)
    avg_late_activity_level = calculate_average(late_activity_levels)

    heart_rate_declined = avg_late_heart_rate < peak_heart_rate * 0.85
    activity_declined = avg_late_activity_level < peak_activity_level * 0.6

    return heart_rate_declined and activity_declined


def explain_classification(classification, heart_rate_ratio, avg_activity_level):

    # Explaination to why a session got its classification
    if classification == "insufficient data":
        return "Not enough valid observations were available to classify this session."
    if classification == "recovering":
        return "Heart rate and activity level both dropped near the end of the session, after an earlier peak."
    if classification == "high activity":
        return f"Heart rate was {heart_rate_ratio:.1f}x baseline and/or activity level ({avg_activity_level:.2f}) was high."
    if classification == "moderate activity":
        return f"Heart rate was {heart_rate_ratio:.1f}x baseline and/or activity level ({avg_activity_level:.2f}) was moderate."
    return f"Heart rate ({heart_rate_ratio:.1f}x baseline) and activity level ({avg_activity_level:.2f}) stayed close to resting levels."


def print_session_report(result):
    print("=" * 55)
    print(f"Session: {result['session_id']}   Participant: {result['participant_id']}")
    print("-" * 55)
    print(
        f"Observations: {result['total_observations']} total, "
        f"{result['valid_observations']} valid, "
        f"{result['invalid_observations']} invalid/flagged"
    )

    if result["classification"] == "insufficient data":
        print("Classification: INSUFFICIENT DATA")
    else:
        print(
            f"Heart rate: avg {result['avg_heart_rate']} bpm "
            f"(min {result['min_heart_rate']}, max {result['max_heart_rate']}, "
            f"baseline {result['baseline_heart_rate']})"
        )
        print(f"Activity level (avg): {result['avg_activity_level']}")
        print(f"Skin response: avg {result['avg_skin_response']} (baseline {result['baseline_skin_response']})")
        print(f"Temperature: avg {result['avg_temperature']} (baseline {result['baseline_temperature']})")
        print(f"Classification: {result['classification'].upper()}")

    print(f"Explanation: {result['explanation']}")
    print("=" * 55)


# Classes

class Participant:
    """
    Person partaking in training sessions, with their personal baseline measurements used for comparison.
    
    baseline_heart_rate is only changed through validity processes.
    """

    def __init__(self, participant_id, baseline_heart_rate, baseline_skin_response, baseline_temperature):
        self.participant_id = participant_id

        self._baseline_heart_rate = None
        self.baseline_heart_rate = baseline_heart_rate  # goes through the setter below

        if baseline_skin_response < 0:
            raise ValueError(f"Invalid baseline skin response: {baseline_skin_response}")
        self.baseline_skin_response = baseline_skin_response

        if not (25.0 <= baseline_temperature <= 45.0):
            raise ValueError(f"Invalid baseline temperature: {baseline_temperature}")
        self.baseline_temperature = baseline_temperature

    @property
    def baseline_heart_rate(self):
        return self._baseline_heart_rate

    @baseline_heart_rate.setter
    def baseline_heart_rate(self, value):
        if not (30 <= value <= 220):
            raise ValueError(f"Invalid baseline heart rate: {value}")
        self._baseline_heart_rate = value

    @classmethod
    def from_profile(cls, profile):
        return cls(
            participant_id=profile["participant_id"],
            baseline_heart_rate=profile["baseline_heart_rate"],
            baseline_skin_response=profile["baseline_skin_response"],
            baseline_temperature=profile["baseline_temperature"],
        )


class Observation:

    """
    One measurement from a wearable device. Validity is defined through validate_observation() at creation.
    """
    def __init__(self, timestamp, heart_rate, skin_response, temperature,
                 activity_level, signal_quality, is_valid):
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity_level = activity_level
        self.signal_quality = signal_quality
        self._is_valid = is_valid  # protected: set once, from validation logic, read-only from outside

    @property
    def is_valid(self):
        return self._is_valid

    @classmethod
    def from_dict(cls, data):

        is_valid, _ = validate_observation(data)
        return cls(
            timestamp=data.get("timestamp"),
            heart_rate=data.get("heart_rate"),
            skin_response=data.get("skin_response"),
            temperature=data.get("temperature"),
            activity_level=data.get("activity_level"),
            signal_quality=data.get("signal_quality"),
            is_valid=is_valid,
        )


class Session:
    """
    A training session HAS A participant and HAS a observation objects
    """
    def __init__(self, session_id, participant):
        self.session_id = session_id
        self.participant = participant
        self._observations = []  # protected: changed only through the methods below

    def add_observation(self, observation):
        self._observations.append(observation)

    def add_raw_observations(self, raw_dicts):
        """Convenience method: build and add Observations from raw dicts."""
        for data in raw_dicts:
            self.add_observation(Observation.from_dict(data))

    @property
    def observations(self):
        return list(self._observations)  # copy, so callers can't mutate our internal list

    def valid_observations(self):
        valid = []
        for observation in self._observations:
            if observation.is_valid:
                valid.append(observation)
        return valid

    def invalid_observations(self):
        invalid = []
        for observation in self._observations:
            if not observation.is_valid:
                invalid.append(observation)
        return invalid


class SessionAnalyzer:
    """
    Analyze one session: gets average, checks them against baseline, picks a 
    classification and checks recovery.

    a SessionAnalyzer HAS A Session.
    """

    def __init__(self, session):
        self.session = session

    @staticmethod
    def classify_intensity(heart_rate_ratio, avg_activity_level):
        """
        Justification: heart_rate_ratio compares to the participant's own baseline. Activity
        level has no baseline in the data, so it uses fixed thresholds instead.
        """
        if heart_rate_ratio >= 2.0 or avg_activity_level >= 0.75:
            return "high activity"
        if heart_rate_ratio >= 1.3 or avg_activity_level >= 0.35:
            return "moderate activity"
        return "resting"

    def analyze(self):
        """Run the full analysis and return a structured result dictionary."""
        valid_readings = self.session.valid_observations()
        result = {
            "session_id": self.session.session_id,
            "participant_id": self.session.participant.participant_id,
            "total_observations": len(self.session.observations),
            "valid_observations": len(valid_readings),
            "invalid_observations": len(self.session.invalid_observations()),
        }

        if len(valid_readings) < MIN_VALID_OBSERVATIONS:
            result["classification"] = "insufficient data"
            result["recovering"] = False
            result["explanation"] = explain_classification("insufficient data", 0, 0)
            return result

        heart_rates = [obs.heart_rate for obs in valid_readings]
        activity_levels = [obs.activity_level for obs in valid_readings]
        skin_responses = [obs.skin_response for obs in valid_readings]
        temperatures = [obs.temperature for obs in valid_readings]

        avg_heart_rate = calculate_average(heart_rates)
        min_heart_rate, max_heart_rate = calculate_min_max(heart_rates)
        avg_activity_level = calculate_average(activity_levels)
        avg_skin_response = calculate_average(skin_responses)
        avg_temperature = calculate_average(temperatures)

        recovering = detect_recovery(heart_rates, activity_levels)

        participant = self.session.participant
        if participant.baseline_heart_rate:
            heart_rate_ratio = avg_heart_rate / participant.baseline_heart_rate
        else:
            heart_rate_ratio = 0

        classification = self.classify_intensity(heart_rate_ratio, avg_activity_level)
        if recovering:
            classification = "recovering"

        result["classification"] = classification
        result["recovering"] = recovering
        result["explanation"] = explain_classification(classification, heart_rate_ratio, avg_activity_level)
        result["avg_heart_rate"] = round(avg_heart_rate, 1)
        result["min_heart_rate"] = min_heart_rate
        result["max_heart_rate"] = max_heart_rate
        result["baseline_heart_rate"] = participant.baseline_heart_rate
        result["avg_activity_level"] = round(avg_activity_level, 2)
        result["avg_skin_response"] = round(avg_skin_response, 2)
        result["baseline_skin_response"] = participant.baseline_skin_response
        result["avg_temperature"] = round(avg_temperature, 2)
        result["baseline_temperature"] = participant.baseline_temperature
        return result

    def print_report(self):
        result = self.analyze()
        print_session_report(result)
        return result

def main():
    from sample_data import build_all_scenarios

    print("SMART FITNESS SESSION ANALYZER")
    print()

    for session_id, profile, raw_observations in build_all_scenarios():
        participant = Participant.from_profile(profile)
        session = Session(session_id, participant)
        session.add_raw_observations(raw_observations)

        analyzer = SessionAnalyzer(session)
        analyzer.print_report()
        print()


if __name__ == "__main__":
    main()
