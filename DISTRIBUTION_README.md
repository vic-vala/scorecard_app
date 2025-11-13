# Scorecard Generator - Distribution Guide

## For End Users

### System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **RAM**: 8GB minimum (16GB recommended for LLM features)
- **Disk Space**: 10GB free space
  - Application: ~300-400MB
  - LLM Model (downloaded on first run): ~5GB
  - LaTeX (downloaded on first run): ~150MB
  - Working files: ~1-2GB
- **Internet Connection**: Required for first-run setup only

### Installation Instructions

1. **Download** the application:
   - Download `Scorecard_Generator_Windows.zip`

2. **Extract** the archive:
   - Right-click on the zip file
   - Select "Extract All..."
   - Choose a destination folder (e.g., `C:\Program Files\Scorecard_Generator`)
   - Click "Extract"

3. **Run** the application:
   - Navigate to the extracted folder
   - Double-click `Scorecard_Generator.exe`
   - **Note**: Windows Defender SmartScreen may show a warning (see Troubleshooting below)

4. **First-Run Setup Wizard**:
   - The setup wizard will appear on first launch
   - Follow the prompts to:
     - Download the LLM model (~5GB, 10-20 minutes)
     - Install TinyTeX LaTeX distribution (~150MB)
   - This setup only runs once
   - You can skip components if needed

5. **Start Using**:
   - After setup completes, the main application will launch
   - Follow the configuration GUI to set up your preferences
   - Add your PDF evaluation forms and Excel grade data
   - Generate scorecards!

### Troubleshooting

#### Windows Defender SmartScreen Warning

When you first run the application, Windows may show a warning:

```
Windows protected your PC
Microsoft Defender SmartScreen prevented an unrecognized app from starting.
```

**This is normal for unsigned applications.** To proceed:

1. Click "More info"
2. Click "Run anyway"

The application is safe - this warning appears because we haven't purchased a code signing certificate.

#### First-Run Setup Fails

**Model Download Fails:**
- Check your internet connection
- You can manually download the model and place it at:
  - `[AppFolder]\configuration\LLM\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` (where `[AppFolder]` is where you extracted the application)
  - Or use the "I already have a model file" option in the wizard

**LaTeX Installation Fails:**
- You can manually install LaTeX:
  - Download MiKTeX: https://miktex.org/download
  - Or TinyTeX: https://yihui.org/tinytex/
- The application will use system-installed LaTeX if available

#### Application Won't Start

1. **Check System Requirements**: Ensure you have Windows 10/11 64-bit
2. **Missing DLL Errors**: Install Visual C++ Redistributable:
   - Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
3. **Antivirus Blocking**: Add an exception for the application folder

#### Model Takes Too Long to Load

- The first time the model loads, it may take 30-60 seconds
- Subsequent loads will be faster
- If you have <16GB RAM, consider using a smaller model

### File Locations

After installation, the application stores data in the extraction folder:

- **Application Executable**: `[AppFolder]\Scorecard_Generator.exe`
- **Bundled Resources** (read-only): `[AppFolder]\_internal\`
- **User Configuration**: `[AppFolder]\configuration\config.json` (created on first run, editable)
- **Downloaded Model**: `[AppFolder]\configuration\LLM\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`
- **LaTeX Distribution**: `[AppFolder]\resources\TinyTeX\`
- **Setup Marker**: `[AppFolder]\resources\.setup_complete`
- **Input Files**: `[AppFolder]\input_files\` (PDFs and Excel)
- **Output Files**: `[AppFolder]\scorecards\` (generated PDFs)
- **Temporary Files**: `[AppFolder]\temporary_files\` (working files)

To reset first-run setup, delete the `.setup_complete` file in the `resources` folder.

### Uninstallation

1. Delete the application folder (where you extracted the zip)
   - This removes all application files, resources, models, and data
2. (Optional) Delete matplotlib cache: `%USERPROFILE%\.matplotlib\`

---

## For Developers

### Building from Source

#### Prerequisites

1. **Python 3.12+** installed and in PATH
2. **All dependencies** installed:
   ```bash
   pip install -r requirements.txt
   ```
3. **PyInstaller** installed:
   ```bash
   pip install pyinstaller
   ```
4. **Windows** machine (for Windows builds)

#### Build Steps

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **Run the build script**:
   ```bash
   build_windows.bat
   ```

   Or manually:
   ```bash
   pyinstaller scorecard.spec
   ```

3. **Find the output**:
   - Folder: `dist\Scorecard_Generator\`
   - Zip: `Scorecard_Generator_Windows.zip`

#### Build Customization

**Change Icon:**
1. Place your icon file (`.ico`) in the project root
2. Edit `scorecard.spec`:
   ```python
   icon='path/to/your/icon.ico'
   ```

**Reduce Size:**
1. Uncomment MKL removal in `scorecard.spec`:
   ```python
   a.binaries = [x for x in a.binaries if not x[0].startswith('mkl')]
   ```
2. This removes ~200-400MB from NumPy/SciPy

**Add Additional Files:**
Edit `scorecard.spec` datas section:
```python
datas=[
    ('configuration/config.json', 'configuration'),
    ('your/additional/file.txt', 'destination/folder'),
],
```

#### Testing in WSL/Linux (Recommended for Development)

**For faster iteration during development, use the Linux/WSL build scripts:**

1. **Quick Development Testing** (no build required):
   ```bash
   ./test_dev.sh
   ```
   Options:
   - Run normally with first-run setup
   - Skip first-run setup for faster testing
   - Force first-run setup (reset)
   - Run smoke tests only

2. **Build for Linux/WSL**:
   ```bash
   ./build_linux.sh
   ```
   Output: `dist/Scorecard_Generator/Scorecard_Generator` (Linux executable)

3. **Run Automated Tests**:
   ```bash
   python3 test_frozen.py
   ```
   Tests:
   - All critical imports (pandas, matplotlib, etc.)
   - Resource path access
   - Configuration loading
   - Tkinter GUI availability
   - First-run setup functionality

4. **Test Built Linux Executable**:
   ```bash
   cd dist/Scorecard_Generator
   ./Scorecard_Generator
   ```

**Benefits of WSL/Linux Testing:**
- ✅ Faster build times (2-3 minutes vs 5-10 minutes on Windows)
- ✅ Test packaging infrastructure without leaving your dev environment
- ✅ Catch issues early before Windows build
- ✅ No need to switch to Windows machine
- ✅ Same PyInstaller spec file works for both platforms

**Note:** Linux executable won't run on Windows. Use this for development testing only. Final distribution should use Windows build.

#### Testing the Windows Build

1. **Test on clean VM**:
   - Use Windows 10/11 VM with **no Python installed**
   - Copy the `dist\Scorecard_Generator\` folder
   - Run the executable
   - Verify all features work

2. **Test First-Run Setup**:
   - Delete `resources/.setup_complete` in the application folder
   - Run the application
   - Verify setup wizard appears and works

3. **Test Core Features**:
   - PDF parsing
   - Excel parsing
   - Data visualization
   - LaTeX compilation
   - LLM inference (if model available)

### Adding Dependencies

When adding new Python packages:

1. Add to `requirements.txt`
2. Test if PyInstaller auto-detects it
3. If not, add to `hiddenimports` in `scorecard.spec`
4. Rebuild and test

### Default Model

The application uses **Meta-Llama-3.1-8B-Instruct-Q4_K_M** as the default LLM model:
- **Source**: HuggingFace (bartowski)
- **URL**: https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
- **Size**: ~5GB
- **Quantization**: Q4_K_M (good balance of quality and size)

The model is automatically downloaded during first-run setup if no URL is provided in the wizard.

### Updating the Model

To change the default model:

1. Edit `src/first_run_setup.py`:
   ```python
   DEFAULT_MODEL_URL = "https://your-model-url.com/model.gguf"
   DEFAULT_MODEL_NAME = "YourModelName.gguf"
   ```
