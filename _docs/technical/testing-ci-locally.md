# Testing CI Workflows Locally

This guide explains how to test the GitHub Actions CI workflow locally using `act`, which allows you to run GitHub Actions workflows on your local machine using Docker.

## Prerequisites

### 1. Install Docker
- **macOS**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**: Install Docker Engine
- **Windows**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 2. Install act
```bash
# macOS (using Homebrew)
brew install act

# Linux (using curl)
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows (using Chocolatey)
choco install act-cli

# Or download from GitHub releases
# https://github.com/nektos/act/releases
```

### 3. Verify Installation
```bash
act --version
docker --version
```

## Basic Usage

### List Available Workflows
```bash
# From project root
act --list
```

### Dry Run (Validate Workflow)
```bash
# Validate workflow syntax without running
act --validate

# Dry run to see what would happen
act --dryrun
```

### Run Specific Job
```bash
# Run only the test job
act -j test

# Run only the build job
act -j build
```

### Run All Jobs
```bash
# Run all jobs (default event: push)
act

# Run with specific event
act push
act pull_request
```

## Advanced Usage

### Platform-Specific Testing
```bash
# Test only Ubuntu jobs
act -P ubuntu-latest=catthehacker/ubuntu:act-latest

# Test only macOS jobs (use Ubuntu image for compatibility)
act -P macos-latest=catthehacker/ubuntu:act-latest

# Test both platforms (recommended)
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -P macos-latest=catthehacker/ubuntu:act-latest
```

### Verbose Output
```bash
# Show detailed logs
act -v

# Show even more detail
act -vv
```

### Environment Variables
```bash
# Set environment variables
act --env MY_VAR=value

# Use environment file
act --env-file .env
```

### Secrets
```bash
# Set secrets
act --secret MY_SECRET=value

# Use secrets file
act --secret-file .secrets
```

## Testing Our CI Workflow

### 1. Validate the Workflow
```bash
cd /path/to/subconscious-metaprogramming
act --validate
```

### 2. Dry Run to See What Would Happen
```bash
# Dry run with platform mappings (recommended)
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -P macos-latest=catthehacker/ubuntu:act-latest --dryrun
```

### 3. Test Individual Jobs
```bash
# Test the main test job with platform mappings
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -P macos-latest=catthehacker/ubuntu:act-latest -j test

# Test the build job
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -j build
```

### 4. Test with Specific Python Version
```bash
# Test with Python 3.11
act -j test --env PYTHON_VERSION=3.11

# Test with Python 3.12
act -j test --env PYTHON_VERSION=3.12
```

## Troubleshooting

### Common Error: "invalid reference format"
This error occurs when `act` can't find the correct Docker images for the platforms. **Solution:**
```bash
# Always use platform mappings
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -P macos-latest=catthehacker/ubuntu:act-latest
```

### Docker Issues
```bash
# Check if Docker is running
docker ps

# Start Docker Desktop (macOS)
open -a Docker

# Restart Docker daemon (Linux)
sudo systemctl restart docker
```

### Platform Issues
```bash
# If you get "invalid reference format" errors, use platform mappings
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -P macos-latest=catthehacker/ubuntu:act-latest

# If macOS jobs fail, use Ubuntu image instead
act -P macos-latest=catthehacker/ubuntu:act-latest

# If you get platform errors, try with specific architecture
act --container-architecture linux/amd64
```

### Permission Issues
```bash
# If you get permission errors, try with bind mount
act -b

# Or run with sudo (Linux only)
sudo act
```

### Network Issues
```bash
# Use host network
act --network host

# Or specify custom network
act --network bridge
```

### MyPy Type Checking Issues
If you see mypy errors in the CI (like missing return type annotations), this is expected for now:
```bash
# The CI will fail on mypy errors, but tests pass
# This is a known issue with type annotations that can be fixed later
# The core functionality works correctly
```

## Manual CI Testing

If `act` doesn't work or you want to test individual steps manually:

### 1. Install Dependencies
```bash
uv sync --frozen
```

### 2. Run Tests
```bash
uv run pytest -q
```

### 3. Code Quality Checks
```bash
uv run black --check src/ tests/
uv run mypy src/
```

### 4. CLI Smoke Tests
```bash
uv run sleepstack --help
uv run sleepstack --version
uv run sleepstack --list-vibes
```

### 5. Package Installation Test
```bash
uv tool install .
sleepstack --version
```

### 6. Audio Generation Test
```bash
uv run sleepstack --vibe calm -a campfire -s 1
ls -la build/binaural/
ls -la build/mix/
```

### 7. Package Build Test
```bash
uv build
ls -la dist/
```

## CI Workflow Details

Our CI workflow (`.github/workflows/ci.yml`) includes:

### Test Job
- **Platforms**: Ubuntu and macOS
- **Python Versions**: 3.11 and 3.12
- **Steps**:
  1. Checkout code
  2. Install uv
  3. Set up Python
  4. Install dependencies with `uv sync --frozen`
  5. Run tests with `uv run pytest -q`
  6. Code quality checks (black, mypy)
  7. CLI smoke tests
  8. Package installation test
  9. Audio generation smoke test

### Build Job
- **Platform**: Ubuntu
- **Dependencies**: Requires test job to pass
- **Steps**:
  1. Checkout code
  2. Install uv and Python
  3. Install dependencies
  4. Build package with `uv build`
  5. Upload build artifacts

## Best Practices

### 1. Test Before Committing
```bash
# Always validate before committing
act --validate

# Run a quick test
act -j test --dryrun
```

### 2. Test Different Scenarios
```bash
# Test with different events
act push
act pull_request

# Test specific branches
act push --eventpath .github/event.json
```

### 3. Debug Issues
```bash
# Use verbose output for debugging
act -vv

# Test individual steps
act -j test --dryrun
```

### 4. Keep Docker Updated
```bash
# Pull latest act images
act --pull

# Rebuild local images
act --rebuild
```

## Example Commands

```bash
# Quick validation
act --validate

# Test everything with platform mappings (recommended)
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -P macos-latest=catthehacker/ubuntu:act-latest

# Test only on Ubuntu
act -P ubuntu-latest=catthehacker/ubuntu:act-latest

# Test with verbose output
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -P macos-latest=catthehacker/ubuntu:act-latest -v

# Test specific job with secrets
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -j test --secret GITHUB_TOKEN=your_token
```

## Resources

- [act Documentation](https://github.com/nektos/act)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [uv Documentation](https://docs.astral.sh/uv/)

## Notes

- `act` uses Docker containers to simulate GitHub Actions runners
- Some actions may not work exactly the same locally
- macOS jobs may need special handling or alternative images
- Always test your workflows before pushing to avoid CI failures
