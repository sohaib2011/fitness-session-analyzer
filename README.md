# Smart Fitness Session Analyzer

**Option: A - Smart Fitness Session Analyzer**

**Student name:** Sohaib Kaiser Latif

**Student number:** solat2590

## Short description

Console-based fitness session analyzer that organizes fitness-session data produced by supplied data generator (`data_generator.py`). The program reads measurements such as heart rate, skin response, temperature, activity level and signal quality, and groups them into training sessions.

It checks whether the measurements are valid, compares them with the participant’s baseline values, and then classifies the session as resting, moderate activity, high activity, recovering, or insufficient data. The program also checks if the participant is recovering towards the end of the session and prints a simple report with the results.


## Class design and responsibilities

| Class | Responsibility |
|---|---|
| Participant | Stores a participant's id and personal baseline heart rate, skin response and temperature. |
| Observation | Shows one measurement frame from the sensor. Knows whether it is valid, via the `from_dict` classmethod, which runs validation at creation time. |
| Session | A training session for one participant. Holds the participant and the list of observations, and exposes helper methods to filter valid/invalid observations. |
| SessionAnalyzer | Takes a `Session` and produces the analysis: summaries, comparison with the baseline values, intensity classification, and recovery detection. Returns a structured result dictionary and prints a report with an explaination (`explain_classification()`). |


## Repository structure

main.py                - all classes and standalone functions

sample_data.py         - builds the demo scenarios using data_generator.py

data_generator.py      - instructor-supplied

example_usage.py       - instructor-supplied

DATA_DESCRIPTION.md    - instructor-supplied

tests.py               - automated tests

requirements.txt       - standard library only

README.md



## Where composition, encapsulation, inheritance and overriding are demonstrated

- **Composition:** `Session` has a `Participant` and a list of `Observation`
objects (`self.participant = participant`, `self._observations = []`)
`SessionAnalyzer` has a `Session` (`self.session = session`). These
 objects are built by combining other objects.
- **Encapsulation:** I used protected attributes like Participant._baseline_heart_rate and Observation._is_valid.   They are accessed through properties instead of directly. baseline_heart_rate also has a setter that checks the value before changing it.
- **Inheritance and overriding:** I did not use inheritance in this design because the classes do not have a clear "is a" relationship. A Session has Observation objects rather than being a type of Observation, so composition fits the design better.
- **Classmethod/staticmethod:** I used `@classmethod` for `Observation.from_dict()` and `Participant.from_profile()` because they create objects from a dictionary instead of having to give every value separately. 
I also used `@staticmethod` for `classify_intensity()` because it only uses the values given to it and does not use `self`.


## Assumptions and classification rules

- A valid measurement needs all six fields. Heart rate must be 30-220 bpm, temperature 25.0-45.0 celsius, activity level 0.0-1.0, skin response 0 or more, and signal quality 0.0-1.0. Signal quality under 0.5 counts as too bad to trust
- A session needs at least three valid measurements to be analysed. If not this will get "insufficient data"
- Heart rate gets compared to the person's own baseline, as a ratio
- Activity level has no baseline and is defined through fixed numbers since its already between 0 and 1 for everyone
- I assumed these thresholds, since the assignment doesn't give exact numbers:
  - heart_rate_ratio >= 2.0 or activity >= 0.75 -> high activity
  - heart_rate_ratio >= 1.3` or activity >= 0.35 -> moderate activity
  - otherwise → resting
- Skin response and temperature also gets compared in baseline, but dont change the classification
- Recovery is checked seperately. Last third of the session gets compared to earlier peak. If heart rate goes below 85% of the peak, and activity below 60, the session returns recovering and overrides whatever it got above.


## Installation and running instructions

```
git clone https://github.com/sohaib2011/fitness-session-analyzer.git
cd fitness-session-analyzer
python3 main.py
```

(The same applies if you uses python instead of python3.)

To run the automated tests:

```
python3 -m unittest tests.py

```


## Example output

```
SMART FITNESS SESSION ANALYZER

=======================================================
Session: Resting   Participant: P001
-------------------------------------------------------
Observations: 10 total, 10 valid, 0 invalid/flagged
Heart rate: avg 64.1 bpm (min 60, max 67, baseline 62)
Activity level (avg): 0.14
Skin response: avg 1.83 (baseline 1.85)
Temperature: avg 32.81 (baseline 32.86)
Classification: RESTING
Explanation: Heart rate (1.0x baseline) and activity level (0.14) stayed close to resting levels.
=======================================================

=======================================================
Session: Moderate activity   Participant: P001
-------------------------------------------------------
Observations: 10 total, 10 valid, 0 invalid/flagged
Heart rate: avg 83.7 bpm (min 69, max 92, baseline 59)
Activity level (avg): 0.51
Skin response: avg 1.47 (baseline 1.14)
Temperature: avg 32.38 (baseline 32.11)
Classification: MODERATE ACTIVITY
Explanation: Heart rate was 1.4x baseline and/or activity level (0.51) was moderate.
=======================================================

=======================================================
Session: High activity   Participant: P001
-------------------------------------------------------
Observations: 10 total, 10 valid, 0 invalid/flagged
Heart rate: avg 122.5 bpm (min 111, max 132, baseline 65)
Activity level (avg): 0.86
Skin response: avg 2.48 (baseline 1.89)
Temperature: avg 32.34 (baseline 31.72)
Classification: HIGH ACTIVITY
Explanation: Heart rate was 1.9x baseline and/or activity level (0.86) was high.
=======================================================

=======================================================
Session: Recovery   Participant: P001
-------------------------------------------------------
Observations: 10 total, 10 valid, 0 invalid/flagged
Heart rate: avg 101.5 bpm (min 77, max 126, baseline 65)
Activity level (avg): 0.47
Skin response: avg 1.82 (baseline 1.45)
Temperature: avg 33.02 (baseline 32.73)
Classification: RECOVERING
Explanation: Heart rate and activity level both dropped near the end of the session, after an earlier peak.
=======================================================

=======================================================
Session: Poor quality data   Participant: P001
-------------------------------------------------------
Observations: 10 total, 0 valid, 10 invalid/flagged
Classification: INSUFFICIENT DATA
Explanation: Not enough valid observations were available to classify this session.
=======================================================
```

## Known limitations

- The numbers used for classification and recovery are just simple guesses.
- Recovery check only looks at the last third of the session. It doesn't look at exact timing between each measurement.
- Skin response and temperature are shown in the report, but dont have an effect in the   classification
