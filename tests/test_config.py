"""Tests for configuration module."""

import pytest

from cognitive_dissonance.config import ExperimentConfig, setup_logging


class TestExperimentConfig:
    """Test ExperimentConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExperimentConfig()

        assert config.model == "ollama_chat/llama3.1:8b"
        assert config.api_base == "http://localhost:11434"
        assert config.api_key == ""
        assert config.temperature == 0.5
        assert config.max_tokens == 512
        assert config.alpha == 0.0
        assert config.rounds == 6
        assert config.use_cot is False
        assert config.dissonance_threshold == 0.7
        assert config.auto_mode == "light"
        assert config.enable_disk_cache is False
        assert config.enable_memory_cache is False

    def test_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("MODEL", "test_model")
        monkeypatch.setenv("API_BASE", "http://test-api:1234")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.setenv("TEMPERATURE", "0.7")
        monkeypatch.setenv("MAX_TOKENS", "256")
        monkeypatch.setenv("ALPHA", "0.3")
        monkeypatch.setenv("ROUNDS", "5")
        monkeypatch.setenv("USE_COT", "true")
        monkeypatch.setenv("DISSONANCE_THRESHOLD", "0.8")
        monkeypatch.setenv("AUTO_MODE", "heavy")
        monkeypatch.setenv("ENABLE_DISK_CACHE", "true")
        monkeypatch.setenv("ENABLE_MEMORY_CACHE", "true")

        config = ExperimentConfig.from_env()

        assert config.model == "test_model"
        assert config.api_base == "http://test-api:1234"
        assert config.api_key == "test-key"
        assert config.temperature == 0.7
        assert config.max_tokens == 256
        assert config.alpha == 0.3
        assert config.rounds == 5
        assert config.use_cot is True
        assert config.dissonance_threshold == 0.8
        assert config.auto_mode == "heavy"
        assert config.enable_disk_cache is True
        assert config.enable_memory_cache is True

    def test_validate_valid_config(self, mock_config):
        """Test validation with valid configuration."""
        # Should not raise any exceptions
        mock_config.validate()

    def test_validate_invalid_alpha(self, mock_config):
        """Test validation with invalid alpha."""
        mock_config.alpha = 1.5
        with pytest.raises(ValueError, match="Alpha must be between"):
            mock_config.validate()

        mock_config.alpha = -0.1
        with pytest.raises(ValueError, match="Alpha must be between"):
            mock_config.validate()

    def test_validate_invalid_dissonance_threshold(self, mock_config):
        """Test validation with invalid dissonance threshold."""
        mock_config.dissonance_threshold = 1.5
        with pytest.raises(ValueError, match="Dissonance threshold must be between"):
            mock_config.validate()

        mock_config.dissonance_threshold = -0.1
        with pytest.raises(ValueError, match="Dissonance threshold must be between"):
            mock_config.validate()

    def test_validate_invalid_rounds(self, mock_config):
        """Test validation with invalid rounds."""
        mock_config.rounds = 0
        with pytest.raises(ValueError, match="Rounds must be"):
            mock_config.validate()

        mock_config.rounds = -1
        with pytest.raises(ValueError, match="Rounds must be"):
            mock_config.validate()

    def test_validate_invalid_temperature(self, mock_config):
        """Test validation with invalid temperature."""
        mock_config.temperature = -0.5
        with pytest.raises(ValueError, match="Temperature must be"):
            mock_config.validate()

    def test_validate_invalid_max_tokens(self, mock_config):
        """Test validation with invalid max_tokens."""
        mock_config.max_tokens = 0
        with pytest.raises(ValueError, match="Max tokens must be"):
            mock_config.validate()

        mock_config.max_tokens = -10
        with pytest.raises(ValueError, match="Max tokens must be"):
            mock_config.validate()

    def test_setup_dspy(self, mock_config, monkeypatch):
        """Test DSPy setup."""
        # Mock dspy functions to prevent actual API calls
        mock_configure_called = False
        mock_configure_cache_called = False

        def mock_configure(**kwargs):
            nonlocal mock_configure_called
            mock_configure_called = True

        def mock_configure_cache(**kwargs):
            nonlocal mock_configure_cache_called
            mock_configure_cache_called = True

        import dspy
        monkeypatch.setattr(dspy, "configure", mock_configure)
        monkeypatch.setattr(dspy, "configure_cache", mock_configure_cache, raising=False)

        # Mock LM class
        class MockLM:
            def __init__(self, *args, **kwargs):
                pass

        monkeypatch.setattr(dspy, "LM", MockLM)

        mock_config.setup_dspy()

        assert mock_configure_called
        assert mock_configure_cache_called


class TestLogging:
    """Test logging configuration."""

    def test_setup_logging(self):
        """Test logging setup."""
        import logging

        # Setup logging with INFO level
        setup_logging(level="INFO")
        assert logging.getLogger().level == logging.INFO

        # Check that loggers are configured
        logger = logging.getLogger("cognitive_dissonance")
        assert logger.level == logging.INFO

        # Test with DEBUG level
        setup_logging(level="DEBUG")
        assert logging.getLogger().level == logging.DEBUG
        logger = logging.getLogger("cognitive_dissonance")
        assert logger.level == logging.DEBUG
