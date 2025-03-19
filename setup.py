from setuptools import setup, find_packages

setup(
    name="virtuoso-trading",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "pyyaml",
        "ccxt",
        "pandas",
        "numpy",
        "aiohttp",
        "websockets",
        "influxdb-client",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "python-multipart",
        'scikit-learn>=1.0.0',
    ],
    python_requires=">=3.8",
) 