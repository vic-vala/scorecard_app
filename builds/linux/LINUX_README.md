# Linux Build Instructions

## Prerequisites
- Python 3.12+
- Virtual environment with dependencies

## Building
1. Activate your virtual environment
2. Run: `PYTHON_BIN="./.venv/bin/python3" ./build_linux.sh`

## Output
- Executable: `dist/Scorecard_Generator/Scorecard_Generator`
- Package: `Scorecard_Generator_Linux.zip`

## Testing
- Test the frozen build: `./test_frozen_linux.sh` (if created)
- Quick dev test: See `../../scripts/test_dev.sh`

## Notes
- This build is for WSL/Linux testing
- For distribution to Linux users, use this build
- Uses the shared `scorecard.spec` in `build/shared/`