"""
Unit Tests for Phase 24 Experiment Framework & 10 Predefined Scenarios.
"""

import pytest

from app.experiments.scenarios import (
    ExperimentScenario,
    ScenarioRunner,
    get_predefined_scenarios,
)


def test_predefined_scenarios_count_and_schemas():
    """Verifies that exactly 10 predefined evaluation scenarios exist with valid parameters."""
    scenarios = get_predefined_scenarios()
    assert len(scenarios) == 10

    scenario_ids = [s.scenario_id for s in scenarios]
    assert len(set(scenario_ids)) == 10  # Unique IDs

    for s in scenarios:
        assert isinstance(s, ExperimentScenario)
        assert s.seed >= 40
        assert s.duration_hours > 0.0
        assert 0.0 <= s.degradation_magnitude <= 2.0


def test_all_10_scenarios_execute_and_pass():
    """
    CRITICAL EVALUATION TEST: Runs all 10 predefined experiment scenarios
    and verifies 100% accuracy against ground truth labels.
    """
    scenarios = get_predefined_scenarios()
    
    passed_count = 0
    for scenario in scenarios:
        res = ScenarioRunner.run_scenario(scenario)
        assert res.scenario_id == scenario.scenario_id
        assert res.passed is True, f"Scenario '{scenario.name}' failed detection!"
        passed_count += 1

    assert passed_count == 10
