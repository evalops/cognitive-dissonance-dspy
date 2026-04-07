"""Data handling for Cognitive Dissonance experiments."""

import logging
from typing import List, Dict, Any, Optional
import dspy

logger = logging.getLogger(__name__)


def get_belief_conflicts() -> List[dspy.Example]:
    """
    Get examples of belief conflicts for training.

    Returns:
        List of Examples with conflicting beliefs and labels
    """
    examples = [
        dspy.Example(
            text1="The capital of France is Paris. It is a beautiful city.",
            text2="Paris is not the capital of France. London holds that title.",
            claim1="The capital of France is Paris",
            claim2="The capital of France is London",
            has_dissonance="yes",
            reconciled="The capital of France is Paris",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="Water boils at 100 degrees Celsius at sea level.",
            text2="Water boils at 90 degrees Celsius at sea level.",
            claim1="Water boils at 100°C at sea level",
            claim2="Water boils at 90°C at sea level",
            has_dissonance="yes",
            reconciled="Water boils at 100 degrees Celsius at sea level",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="The Earth orbits around the Sun.",
            text2="The Sun and all planets orbit around Earth.",
            claim1="The Earth orbits around the Sun",
            claim2="The Sun orbits around Earth",
            has_dissonance="yes",
            reconciled="The Earth orbits around the Sun",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="Mount Everest is the tallest mountain on Earth.",
            text2="Mount Everest is located in the Himalayas.",
            claim1="Mount Everest is the tallest mountain",
            claim2="Mount Everest is in the Himalayas",
            has_dissonance="no",
            reconciled="Mount Everest is the tallest mountain on Earth, located in the Himalayas",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="Python is a programming language created in 1991.",
            text2="Python was created by Guido van Rossum.",
            claim1="Python was created in 1991",
            claim2="Python was created by Guido van Rossum",
            has_dissonance="no",
            reconciled="Python is a programming language created by Guido van Rossum in 1991",
        ).with_inputs("text1", "text2"),
    ]

    logger.info(f"Loaded {len(examples)} belief conflict examples")
    return examples


def get_dev_labeled() -> List[dspy.Example]:
    """
    Get labeled development set for evaluation.

    Returns:
        List of Examples with ground truth labels
    """
    examples = get_belief_conflicts()

    # Add some more complex examples for development
    additional = [
        dspy.Example(
            text1="Artificial intelligence will replace all human jobs by 2030.",
            text2="AI can augment human capabilities but cannot replace human creativity.",
            claim1="AI will replace all human jobs by 2030",
            claim2="AI cannot replace human creativity",
            has_dissonance="yes",
            reconciled="AI will augment human capabilities and change the job market, but human creativity remains irreplaceable",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="Climate change is primarily caused by human activities.",
            text2="Global temperatures have been rising since the industrial revolution.",
            claim1="Climate change is caused by humans",
            claim2="Temperatures have risen since industrialization",
            has_dissonance="no",
            reconciled="Climate change, evidenced by rising temperatures since the industrial revolution, is primarily caused by human activities",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="The speed of light is constant in a vacuum.",
            text2="Light travels slower through water than through air.",
            claim1="Light speed is constant in vacuum",
            claim2="Light slows in water",
            has_dissonance="no",
            reconciled="The speed of light is constant in a vacuum but varies when traveling through different media",
        ).with_inputs("text1", "text2"),
    ]

    examples.extend(additional)
    logger.info(f"Loaded {len(examples)} labeled development examples")
    return examples


def get_train_unlabeled() -> List[dspy.Example]:
    """
    Get unlabeled training set for co-training.

    Returns:
        List of Examples without labels
    """
    examples = [
        dspy.Example(
            text1="The human brain contains approximately 86 billion neurons.",
            text2="The brain uses about 20% of the body's energy.",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="Shakespeare wrote Romeo and Juliet in 1595.",
            text2="Romeo and Juliet is set in Verona, Italy.",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="The Great Wall of China is visible from space.",
            text2="The Great Wall is actually not visible from space without aid.",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="Coffee is the world's second most traded commodity.",
            text2="Oil is the most traded commodity globally.",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="Antibiotics kill bacteria but not viruses.",
            text2="The common cold is caused by a virus.",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="The moon affects Earth's tides.",
            text2="The sun also influences tidal patterns.",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="Diamond is the hardest natural material.",
            text2="Graphene is stronger than diamond.",
        ).with_inputs("text1", "text2"),

        dspy.Example(
            text1="The Amazon rainforest produces 20% of Earth's oxygen.",
            text2="Most of Earth's oxygen comes from ocean phytoplankton.",
        ).with_inputs("text1", "text2"),
    ]

    # Add more unlabeled examples
    for i in range(20):
        examples.append(
            dspy.Example(
                text1=f"Statement A number {i}: This is a fact.",
                text2=f"Statement B number {i}: This might contradict or support A.",
            ).with_inputs("text1", "text2")
        )

    logger.info(f"Loaded {len(examples)} unlabeled training examples")
    return examples


def validate_dataset(
    dataset: List[dspy.Example],
    require_labels: bool = False
) -> None:
    """
    Validate a dataset for required fields.

    Args:
        dataset: List of Examples to validate
        require_labels: Whether to require label fields

    Raises:
        ValueError: If dataset is invalid
    """
    if not dataset:
        raise ValueError("Dataset is empty")

    required_inputs = ["text1", "text2"]
    required_labels = ["has_dissonance", "reconciled"] if require_labels else []

    for i, example in enumerate(dataset):
        # Check required input fields
        for field in required_inputs:
            if field not in example.inputs():
                raise ValueError(f"Example {i} missing required input field: {field}")

        # Check required label fields if needed
        if require_labels:
            for field in required_labels:
                if not hasattr(example, field):
                    raise ValueError(f"Example {i} missing required label field: {field}")

    logger.info(f"Dataset validation passed for {len(dataset)} examples")


def get_external_knowledge(url: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch external knowledge from API.

    Args:
        url: Optional URL override

    Returns:
        Dictionary with knowledge data
    """
    import os

    if url is None:
        url = os.getenv("WIKI1K_URL", "http://20.102.90.50:2017/wiki1k")

    try:
        logger.info(f"Fetching external knowledge from: {url}")
        # In production, make actual API call
        # response = requests.get(url, timeout=10)
        # return response.json()

        # For now, return mock data
        return {
            "status": "available",
            "entries": 1000,
            "url": url
        }
    except Exception as e:
        logger.error(f"Failed to fetch external knowledge: {e}")
        return {"status": "error", "error": str(e)}
