# Contributing to Virtuoso

Thank you for your interest in contributing to Virtuoso! This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/Virtuoso.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
5. Install dependencies: `pip install -e .`
6. Install test dependencies: `pip install -r config/ci/requirements-test.txt`

## Code Style

This project follows PEP 8 style guidelines with the following tools:
- Black for code formatting
- Flake8 for linting
- isort for import sorting

## Testing

Run tests with pytest:
```
pytest -c config/ci/pytest.ini
```

## Pull Request Process

1. Ensure your code follows the style guidelines
2. Update documentation as needed
3. Make sure all tests pass
4. Create a pull request with a clear description of the changes

## Project Structure

- `src/` - Main source code
- `tests/` - Test suite
- `docs/` - Documentation
- `examples/` - Example code
- `scripts/` - Utility scripts
- `assets/` - Static assets
- `profiling/` - Performance profiling tools
- `config/` - Configuration files

## License

By contributing, you agree that your contributions will be licensed under the project's license. 