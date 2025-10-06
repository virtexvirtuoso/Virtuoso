from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="virtuoso",
    version="1.0.0",
    author="Fil0s",
    author_email="your.email@example.com",  # Replace with actual email
    description="Advanced cryptocurrency trading system with multi-factor analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fil0s/Virtuoso",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "pyyaml",
        "ccxt",
        "pandas",
        "numpy",
        "aiohttp",
        "aiofiles",
        "websockets",
        "influxdb-client",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "python-multipart",
        'scikit-learn>=1.0.0',
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "black",
            "isort",
            "flake8",
            "mypy",
            "pre-commit",
        ],
    },
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "virtuoso=src.main:main",
        ],
    },
) 