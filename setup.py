from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="cognitive-dissonance-dspy",
    version="0.1.0",
    author="Cognitive Dissonance Team",
    author_email="team@cognitive-dissonance.ai",
    description="A DSPy-based framework for detecting and resolving cognitive dissonance in multi-agent LLM systems.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/evalops/cognitive-dissonance-dspy",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "ruff>=0.1.0",
            "black>=22.0.0",
            "isort>=5.0.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cognitive-dissonance=cognitive_dissonance.main:main",
            "cd-demo=cognitive_dissonance.main:demo_basic_usage",
        ],
    },
)
