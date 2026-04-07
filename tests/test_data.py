"""Tests for data module."""

import dspy
import pytest

from cognitive_dissonance.data import (
    get_belief_conflicts,
    get_dev_labeled,
    get_external_knowledge,
    get_train_unlabeled,
    validate_dataset,
)


class TestDataLoading:
    """Test data loading functions."""

    def test_get_belief_conflicts(self):
        """Test loading belief conflict examples."""
        examples = get_belief_conflicts()

        assert len(examples) > 0
        assert all(isinstance(ex, dspy.Example) for ex in examples)

        # Check first example
        first = examples[0]
        assert hasattr(first, "text1")
        assert hasattr(first, "text2")
        assert hasattr(first, "has_dissonance")
        assert hasattr(first, "reconciled")
        assert "text1" in first.inputs()
        assert "text2" in first.inputs()

    def test_get_dev_labeled(self):
        """Test loading labeled development set."""
        examples = get_dev_labeled()

        assert len(examples) > 0
        assert all(isinstance(ex, dspy.Example) for ex in examples)

        # Should have more examples than just belief_conflicts
        assert len(examples) >= len(get_belief_conflicts())

        # Check all have required fields
        for ex in examples:
            assert hasattr(ex, "text1")
            assert hasattr(ex, "text2")
            assert hasattr(ex, "has_dissonance")
            assert hasattr(ex, "reconciled")

    def test_get_train_unlabeled(self):
        """Test loading unlabeled training set."""
        examples = get_train_unlabeled()

        assert len(examples) > 0
        assert all(isinstance(ex, dspy.Example) for ex in examples)

        # Check all have input fields but not necessarily labels
        for ex in examples:
            assert "text1" in ex.inputs()
            assert "text2" in ex.inputs()


class TestDataValidation:
    """Test data validation functions."""

    def test_validate_dataset_valid(self, sample_examples):
        """Test validation with valid dataset."""
        # Should not raise any exceptions
        validate_dataset(sample_examples, require_labels=True)
        validate_dataset(sample_examples, require_labels=False)

    def test_validate_dataset_empty(self):
        """Test validation with empty dataset."""
        with pytest.raises(ValueError, match="Dataset is empty"):
            validate_dataset([])

    def test_validate_dataset_missing_inputs(self):
        """Test validation with missing input fields."""
        bad_examples = [
            dspy.Example(text1="test").with_inputs("text1")  # Missing text2
        ]

        with pytest.raises(ValueError, match="missing required input field: text2"):
            validate_dataset(bad_examples)

    def test_validate_dataset_missing_labels(self):
        """Test validation with missing label fields."""
        bad_examples = [
            dspy.Example(
                text1="test1",
                text2="test2"
            ).with_inputs("text1", "text2")  # Missing labels
        ]

        # Should pass without requiring labels
        validate_dataset(bad_examples, require_labels=False)

        # Should fail when requiring labels
        with pytest.raises(ValueError, match="missing required label field"):
            validate_dataset(bad_examples, require_labels=True)

    def test_validate_dataset_partial_labels(self):
        """Test validation with partial labels."""
        bad_examples = [
            dspy.Example(
                text1="test1",
                text2="test2",
                has_dissonance="yes"  # Missing reconciled
            ).with_inputs("text1", "text2")
        ]

        with pytest.raises(ValueError, match="missing required label field: reconciled"):
            validate_dataset(bad_examples, require_labels=True)


class TestExternalKnowledge:
    """Test external knowledge functions."""

    def test_get_external_knowledge_default(self):
        """Test getting external knowledge with default URL."""
        result = get_external_knowledge()

        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] in ["available", "error"]

    def test_get_external_knowledge_custom_url(self):
        """Test getting external knowledge with custom URL."""
        custom_url = "http://custom-api:8080/knowledge"
        result = get_external_knowledge(url=custom_url)

        assert isinstance(result, dict)
        assert "status" in result

        if result["status"] == "available":
            assert "url" in result
            assert result["url"] == custom_url

    def test_get_external_knowledge_from_env(self, monkeypatch):
        """Test getting external knowledge from environment variable."""
        test_url = "http://test-wiki:3000/api"
        monkeypatch.setenv("WIKI1K_URL", test_url)

        result = get_external_knowledge()

        assert isinstance(result, dict)
        if result["status"] == "available":
            assert result["url"] == test_url


class TestDataConsistency:
    """Test data consistency and quality."""

    def test_labeled_data_consistency(self):
        """Test that all labeled data has consistent format."""
        examples = get_dev_labeled()

        for ex in examples:
            # Check dissonance values are normalized
            assert ex.has_dissonance in ["yes", "no"]

            # Check reconciled claim is non-empty
            assert ex.reconciled
            assert len(ex.reconciled) > 0

            # Check input texts are non-empty
            assert ex.text1 and len(ex.text1) > 0
            assert ex.text2 and len(ex.text2) > 0

    def test_unlabeled_data_consistency(self):
        """Test that unlabeled data has consistent format."""
        examples = get_train_unlabeled()

        for ex in examples:
            # Check input texts are non-empty
            assert ex.text1 and len(ex.text1) > 0
            assert ex.text2 and len(ex.text2) > 0

            # Check inputs are properly set
            assert "text1" in ex.inputs()
            assert "text2" in ex.inputs()
