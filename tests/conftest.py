"""Shared fixtures for tests."""

import dspy
import pytest

from cognitive_dissonance.config import ExperimentConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = ExperimentConfig(
        model="mock_model",
        api_base="http://mock-api:11434",
        api_key="mock-key",
        temperature=0.5,
        max_tokens=100,
        alpha=0.1,
        rounds=2,
        use_cot=False,
        dissonance_threshold=0.7,
        auto_mode="light",
        enable_disk_cache=False,
        enable_memory_cache=False,
    )
    return config


@pytest.fixture
def mock_lm():
    """Create a mock language model."""
    # Use a simple mock that returns predictable outputs
    class MockLM:
        def __call__(self, *args, **kwargs):
            return {"text": "mock response", "choices": [{"text": "mock response"}]}

    return MockLM()


@pytest.fixture
def sample_texts():
    """Sample texts for testing."""
    return {
        "text1": "The capital of France is Paris.",
        "text2": "Paris is not the capital of France.",
        "text3": "Water boils at 100 degrees Celsius.",
        "text4": "Water boils at 90 degrees Celsius.",
        "compatible1": "Python is a programming language.",
        "compatible2": "Python was created by Guido van Rossum.",
    }


@pytest.fixture
def sample_examples():
    """Sample DSPy examples for testing."""
    examples = [
        dspy.Example(
            text1="The Earth is round.",
            text2="The Earth is flat.",
            has_dissonance="yes",
            reconciled="The Earth is round.",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="Coffee contains caffeine.",
            text2="Tea also contains caffeine.",
            has_dissonance="no",
            reconciled="Both coffee and tea contain caffeine.",
        ).with_inputs("text1", "text2"),
    ]
    return examples


@pytest.fixture
def mock_prediction():
    """Create a mock prediction."""
    pred = dspy.Prediction()
    pred.claim = "mock claim"
    pred.confidence = "medium"
    pred.has_dissonance = "yes"
    pred.reconciled = "mock reconciled claim"
    return pred
