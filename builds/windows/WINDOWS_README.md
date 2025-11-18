# Windows Build Instructions

## Prerequisites  
- Python 3.12+
- PowerShell (for zip creation)
- All dependencies installed

## Building
1. Open Command Prompt
2. Run: `build_windows.bat`

## Output
- Executable: `dist\Scorecard_Generator\Scorecard_Generator.exe`
- Package: `Scorecard_Generator_Windows.zip`

## Distribution
Share the `Scorecard_Generator_Windows.zip` with users
Users extract and run `Scorecard_Generator.exe`

## Notes
- Requires Windows to build
- Uses the shared `scorecard.spec` in `build/shared/`
- First-run wizard will install TinyTeX and download model