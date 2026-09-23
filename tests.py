import unittest

from main import (
    Participant,
    Observation,
    Session,
    SessionAnalyzer,
    validate_observation,
    calculate_average,
    calculate_min_max,
    detect_recovery,
    explain_classification,
)


class TestValidation(unittest.TestCase):

    def test_valid_observation_passes(self):
        data = {"timestamp": 1, "heart_rate": 70, "skin_response": 1.0,
                 "temperature": 32.0, "activity_level": 0.1, "signal_quality": 0.9}
        is_valid, reason = validate_observation(data)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "ok")

    def test_missing_field_is_rejected(self):
        data = {"timestamp": 1, "heart_rate": 70, "skin_response": 1.0,
                 "activity_level": 0.1, "signal_quality": 0.9}  # no temperature
        is_valid, reason = validate_observation(data)
        self.assertFalse(is_valid)
        self.assertIn("missing field", reason)

    def test_impossible_heart_rate_is_rejected(self):
        data = {"timestamp": 1, "heart_rate": 500, "skin_response": 1.0,
                 "temperature": 32.0, "activity_level": 0.1, "signal_quality": 0.9}
        is_valid, _ = validate_observation(data)
        self.assertFalse(is_valid)

    def test_poor_signal_quality_is_rejected(self):
        data = {"timestamp": 1, "heart_rate": 70, "skin_response": 1.0,
                 "temperature": 32.0, "activity_level": 0.1, "signal_quality": 0.1}
        is_valid, reason = validate_observation(data)
        self.assertFalse(is_valid)
        self.assertIn("signal quality", reason)

    def test_negative_skin_response_is_rejected(self):
        data = {"timestamp": 1, "heart_rate": 70, "skin_response": -0.5,
                 "temperature": 32.0, "activity_level": 0.1, "signal_quality": 0.9}
        is_valid, _ = validate_observation(data)
        self.assertFalse(is_valid)


class TestCalculations(unittest.TestCase):

    def test_calculate_average(self):
        self.assertEqual(calculate_average([1, 2, 3]), 2.0)

    def test_calculate_average_empty_list(self):
        self.assertEqual(calculate_average([]), 0.0)

    def test_calculate_min_max(self):
        self.assertEqual(calculate_min_max([5, 1, 9, 3]), (1, 9))

    def test_detect_recovery_true(self):
        heart_rates = [150, 158, 160, 140, 110, 90, 80]
        activity = [0.8, 0.85, 0.88, 0.6, 0.4, 0.2, 0.1]
        self.assertTrue(detect_recovery(heart_rates, activity))

    def test_detect_recovery_false_when_sustained_high(self):
        heart_rates = [150, 155, 158, 160, 159, 157]
        activity = [0.8, 0.85, 0.9, 0.9, 0.88, 0.87]
        self.assertFalse(detect_recovery(heart_rates, activity))

    def test_detect_recovery_false_with_too_few_points(self):
        self.assertFalse(detect_recovery([100, 90], [0.5, 0.3]))


class TestClassification(unittest.TestCase):

    def test_classify_resting(self):
        result = SessionAnalyzer.classify_intensity(66 / 68, 0.06)
        self.assertEqual(result, "resting")

    def test_classify_moderate(self):
        result = SessionAnalyzer.classify_intensity(96 / 68, 0.42)
        self.assertEqual(result, "moderate activity")

    def test_classify_high(self):
        result = SessionAnalyzer.classify_intensity(160 / 68, 0.9)
        self.assertEqual(result, "high activity")


class TestExplanation(unittest.TestCase):

    def test_explanation_is_given_for_every_classification(self):
        # each known classification label must produce a non-empty sentence
        for label in ["resting", "moderate activity", "high activity", "recovering", "insufficient data"]:
            sentence = explain_classification(label, 1.2, 0.3)
            self.assertIsInstance(sentence, str)
            self.assertTrue(len(sentence) > 0)


class TestParticipant(unittest.TestCase):

    def test_valid_baseline_values_are_stored(self):
        participant = Participant("P1", 70, 1.5, 32.0)
        self.assertEqual(participant.baseline_heart_rate, 70)
        self.assertEqual(participant.baseline_skin_response, 1.5)
        self.assertEqual(participant.baseline_temperature, 32.0)

    def test_invalid_baseline_heart_rate_raises(self):
        with self.assertRaises(ValueError):
            Participant("P1", 999, 1.5, 32.0)

    def test_from_profile_builds_matching_participant(self):
        profile = {
            "participant_id": "P002",
            "baseline_heart_rate": 72,
            "baseline_skin_response": 1.8,
            "baseline_temperature": 32.4,
        }
        participant = Participant.from_profile(profile)
        self.assertEqual(participant.participant_id, "P002")
        self.assertEqual(participant.baseline_heart_rate, 72)


class TestSessionComposition(unittest.TestCase):
    """Checks that a Session correctly holds a Participant and Observations
    (the composition relationship required by the assignment)."""

    def setUp(self):
        self.participant = Participant("P1", 70, 1.5, 32.0)
        self.session = Session("Session test", self.participant)

    def test_session_holds_its_participant(self):
        self.assertIs(self.session.participant, self.participant)

    def test_add_raw_observations_creates_observation_objects(self):
        raw = [
            {"timestamp": 1, "heart_rate": 70, "skin_response": 1.0,
             "temperature": 32.0, "activity_level": 0.1, "signal_quality": 0.9},
            {"timestamp": 2, "heart_rate": 500, "skin_response": 1.0,   # invalid on purpose
             "temperature": 32.0, "activity_level": 0.1, "signal_quality": 0.9},
        ]
        self.session.add_raw_observations(raw)
        self.assertEqual(len(self.session.observations), 2)
        for observation in self.session.observations:
            self.assertIsInstance(observation, Observation)
        self.assertEqual(len(self.session.valid_observations()), 1)
        self.assertEqual(len(self.session.invalid_observations()), 1)


class TestSessionAnalyzer(unittest.TestCase):

    def test_insufficient_data_when_too_few_valid_observations(self):
        participant = Participant("P1", 70, 1.5, 32.0)
        session = Session("Session test", participant)
        session.add_raw_observations([
            {"timestamp": 1, "heart_rate": 70, "skin_response": 1.0,
             "temperature": 32.0, "activity_level": 0.1, "signal_quality": 0.9},
        ])  # only one valid observation, minimum is 3

        analyzer = SessionAnalyzer(session)
        result = analyzer.analyze()
        self.assertEqual(result["classification"], "insufficient data")
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
