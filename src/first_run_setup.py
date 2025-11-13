"""
First-run setup module for ASU Scorecard Generator.

Handles:
- GGUF model download with progress tracking
- TinyTeX installation
- Setup completion tracking
"""

import os
import sys
import hashlib
import requests
from pathlib import Path
from typing import Optional
from tqdm import tqdm

# Default GGUF model URL
DEFAULT_MODEL_URL = "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
DEFAULT_MODEL_NAME = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"


class FirstRunSetup:
    """Manages first-run setup tasks for the application."""

    def __init__(self, config=None):
        """
        Initialize setup manager.

        Args:
            config: Optional configuration dict with paths
        """
        from src.resource_utils import get_resource_path, ensure_resources_dir, get_project_root

        # Get project root and resources directory
        self.project_root = get_project_root()
        self.resources_dir = ensure_resources_dir()

        # Setup completion marker in resources directory
        self.setup_complete_marker = self.resources_dir / '.setup_complete'

        # GGUF model path from config or default
        if config and 'paths' in config and 'gguf_path' in config['paths']:
            gguf_path_str = config['paths']['gguf_path']
            # Convert relative path to absolute
            if not Path(gguf_path_str).is_absolute():
                self.model_path = self.project_root / gguf_path_str
            else:
                self.model_path = Path(gguf_path_str)
        else:
            # Default fallback
            self.model_path = self.project_root / 'configuration' / 'LLM' / DEFAULT_MODEL_NAME

        # Ensure model directory exists
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        # TinyTeX in resources directory
        self.tinytex_dir = self.resources_dir / 'TinyTeX'
        self.tinytex_dir.mkdir(parents=True, exist_ok=True)

    def is_first_run(self) -> bool:
        """
        Check if this is the first run of the application.

        Returns:
            True if setup has not been completed yet
        """
        return not self.setup_complete_marker.exists()

    def mark_setup_complete(self):
        """Mark setup as completed by creating marker file."""
        self.setup_complete_marker.touch()
        print(f"✅ Setup marked as complete")

    def download_model(
        self,
        url: str,
        expected_sha256: Optional[str] = None,
        progress_callback=None
    ) -> bool:
        """
        Download GGUF model from URL with progress tracking.

        Args:
            url: URL to download model from
            expected_sha256: Optional SHA256 checksum for verification
            progress_callback: Optional callback function for progress updates

        Returns:
            True if download successful, False otherwise
        """
        try:
            print(f"📥 Downloading model from: {url}")
            print(f"📁 Destination: {self.model_path}")

            # Start download with streaming
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))

            # Download with progress bar
            with open(self.model_path, 'wb') as f:
                if total_size == 0:
                    # No content-length header
                    f.write(response.content)
                else:
                    with tqdm(
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        desc="Downloading model"
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                                if progress_callback:
                                    progress_callback(pbar.n, total_size)

            print("✅ Model download complete")

            # Verify checksum if provided
            if expected_sha256:
                print("🔍 Verifying model integrity...")
                if self.verify_model(expected_sha256):
                    print("✅ Model verification successful")
                    return True
                else:
                    print("❌ Model verification failed!")
                    self.model_path.unlink()  # Delete corrupted file
                    return False

            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Download failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during download: {e}")
            return False

    def verify_model(self, expected_sha256: str) -> bool:
        """
        Verify model file integrity using SHA256 checksum.

        Args:
            expected_sha256: Expected SHA256 hash

        Returns:
            True if checksum matches, False otherwise
        """
        if not self.model_path.exists():
            return False

        sha256 = hashlib.sha256()
        with open(self.model_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        actual_hash = sha256.hexdigest()
        return actual_hash.lower() == expected_sha256.lower()

    def model_exists(self) -> bool:
        """
        Check if model file already exists.

        Returns:
            True if model exists and is not empty
        """
        return self.model_path.exists() and self.model_path.stat().st_size > 0

    def install_tinytex(self) -> bool:
        """
        Install TinyTeX LaTeX distribution.

        Returns:
            True if installation successful, False otherwise
        """
        import subprocess
        import urllib.request
        import zipfile
        import tarfile
        import platform

        try:
            print("📦 Installing TinyTeX...")
            print("   This may take 5-10 minutes depending on your connection...")

            # Direct installation approach (more reliable than pytinytex)
            system = platform.system()

            if system == "Windows":
                installer_url = "https://github.com/rstudio/tinytex-releases/releases/download/v2025.11/tinitex.zip"
                installer_file = self.tinytex_dir.parent / "tinytex_installer.zip"
            elif system == "Linux":
                installer_url = "https://github.com/rstudio/tinytex-releases/releases/download/v2025.11/tinitex.tar.gz"
                installer_file = self.tinytex_dir.parent / "tinytex_installer.tar.gz"
            elif system == "Darwin":  # macOS
                installer_url = "https://github.com/rstudio/tinytex-releases/releases/download/v2025.11/tinitex.tgz"
                installer_file = self.tinytex_dir.parent / "tinytex_installer.tgz"
            else:
                print(f"❌ Unsupported platform: {system}")
                return False

            # Download TinyTeX
            print(f"   Downloading from {installer_url}...")
            try:
                with tqdm(
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc="Downloading TinyTeX"
                ) as pbar:
                    def report_progress(block_num, block_size, total_size):
                        if total_size > 0:
                            pbar.total = total_size
                            pbar.update(block_size)

                    urllib.request.urlretrieve(installer_url, installer_file, reporthook=report_progress)
            except Exception as e:
                print(f"❌ Download failed: {e}")
                return False

            # Extract TinyTeX
            print("   Extracting TinyTeX...")
            try:
                if system == "Windows":
                    with zipfile.ZipFile(installer_file, 'r') as zip_ref:
                        # Extract to parent, then rename to tinytex_dir
                        extract_path = self.tinytex_dir.parent
                        zip_ref.extractall(extract_path)
                        # The zip contains a folder named something like "TinyTeX"
                        # Rename it to our target directory name
                        extracted_folder = extract_path / ".TinyTeX"
                        if extracted_folder.exists():
                            if self.tinytex_dir.exists():
                                import shutil
                                shutil.rmtree(self.tinytex_dir)
                            extracted_folder.rename(self.tinytex_dir)
                else:
                    with tarfile.open(installer_file, 'r:gz') as tar_ref:
                        extract_path = self.tinytex_dir.parent
                        tar_ref.extractall(extract_path)
                        extracted_folder = extract_path / ".TinyTeX"
                        if extracted_folder.exists():
                            if self.tinytex_dir.exists():
                                import shutil
                                shutil.rmtree(self.tinytex_dir)
                            extracted_folder.rename(self.tinytex_dir)
            except Exception as e:
                print(f"❌ Extraction failed: {e}")
                if installer_file.exists():
                    installer_file.unlink()
                return False

            # Clean up installer
            if installer_file.exists():
                installer_file.unlink()

            print("✅ TinyTeX installation complete")

            # Install required packages using tlmgr
            print("📦 Installing required LaTeX packages...")
            tlmgr_path = self.get_latex_binary_path()
            if tlmgr_path:
                tlmgr_dir = Path(tlmgr_path).parent
                tlmgr_bin = tlmgr_dir / ('tlmgr.bat' if system == "Windows" else 'tlmgr')

                if tlmgr_bin.exists():
                    required_packages = [
                        'tcolorbox',
                        'tabularx',
                        'xcolor',
                        'geometry',
                        'graphicx',
                        'booktabs',
                        'pgf',
                        'environ',
                        'trimspaces',
                        'etoolbox'
                    ]

                    for package in required_packages:
                        print(f"  Installing {package}...")
                        try:
                            subprocess.run(
                                [str(tlmgr_bin), 'install', package],
                                check=True,
                                capture_output=True,
                                timeout=120
                            )
                        except subprocess.TimeoutExpired:
                            print(f"  ⚠️  Warning: {package} installation timed out")
                        except Exception as e:
                            print(f"  ⚠️  Warning: Could not install {package}: {e}")

            print("✅ LaTeX packages installation complete")
            return True

        except Exception as e:
            print(f"❌ TinyTeX installation failed: {e}")
            print("⚠️  You may need to install LaTeX manually")
            import traceback
            traceback.print_exc()
            return False

    def tinytex_exists(self) -> bool:
        """
        Check if TinyTeX is already installed.

        Returns:
            True if TinyTeX directory exists
        """
        # Check for bin directory which should contain pdflatex
        bin_dir = self.tinytex_dir / 'bin'
        return bin_dir.exists() and any(bin_dir.iterdir())

    def get_latex_binary_path(self) -> Optional[str]:
        """
        Get path to pdflatex binary.

        Returns:
            Path to pdflatex or None if not found
        """
        # Check in TinyTeX installation
        if self.tinytex_exists():
            # TinyTeX structure: TinyTeX/bin/x86_64-linux/pdflatex (or similar)
            bin_dir = self.tinytex_dir / 'bin'
            for subdir in bin_dir.iterdir():
                if subdir.is_dir():
                    pdflatex = subdir / 'pdflatex'
                    if pdflatex.exists():
                        return str(pdflatex)

        # Fallback: check system PATH
        import shutil
        system_pdflatex = shutil.which('pdflatex')
        if system_pdflatex:
            return system_pdflatex

        return None

    def add_tinytex_to_path(self) -> bool:
        """
        Add TinyTeX bin directory to system PATH.

        This allows PyLaTeX and other tools to find pdflatex.

        Returns:
            True if TinyTeX was added to PATH, False otherwise
        """
        if not self.tinytex_exists():
            return False

        # Find the bin directory with pdflatex
        bin_dir = self.tinytex_dir / 'bin'
        latex_bin_dir = None

        import platform
        system = platform.system()

        for subdir in bin_dir.iterdir():
            if subdir.is_dir():
                # Windows uses pdflatex.exe
                pdflatex_name = 'pdflatex.exe' if system == "Windows" else 'pdflatex'
                pdflatex = subdir / pdflatex_name
                if pdflatex.exists():
                    latex_bin_dir = str(subdir)
                    break

        if not latex_bin_dir:
            return False

        # Add to PATH if not already present
        current_path = os.environ.get('PATH', '')
        if latex_bin_dir not in current_path:
            os.environ['PATH'] = f"{latex_bin_dir}{os.pathsep}{current_path}"
            print(f"✅ Added TinyTeX to PATH: {latex_bin_dir}")
            return True

        return True

    def get_model_path(self) -> Optional[Path]:
        """
        Get path to GGUF model file.

        Returns:
            Path to model if it exists, None otherwise
        """
        if self.model_exists():
            return self.model_path
        return None

    def run_setup(self, model_url: Optional[str] = None, model_sha256: Optional[str] = None) -> bool:
        """
        Run complete first-run setup process.

        Args:
            model_url: Optional URL to download model from
            model_sha256: Optional SHA256 checksum for model verification

        Returns:
            True if setup completed successfully
        """
        print("\n" + "="*60)
        print("  ASU SCORECARD GENERATOR - FIRST RUN SETUP")
        print("="*60 + "\n")

        success = True

        # Step 1: Model download
        if not self.model_exists():
            if model_url:
                print("\n📥 STEP 1: Downloading LLM Model")
                print(f"This is a large file (~5GB) and may take 10-20 minutes.\n")
                if not self.download_model(model_url, model_sha256):
                    print("⚠️  Model download failed. You can add a model manually later.")
                    print(f"   Place your GGUF model file at: {self.model_path}")
                    success = False
            else:
                print("\n⚠️  STEP 1: No model URL provided")
                print(f"   To use LLM features, place a GGUF model file at:")
                print(f"   {self.model_path}")
        else:
            print("\n✅ Model already exists, skipping download")

        # Step 2: TinyTeX installation
        if not self.tinytex_exists():
            print("\n📦 STEP 2: Installing TinyTeX")
            print("This will download and install a minimal LaTeX distribution (~150MB).\n")
            if not self.install_tinytex():
                print("⚠️  TinyTeX installation failed.")
                print("   You may need to install LaTeX manually for PDF generation.")
                success = False
        else:
            print("\n✅ TinyTeX already installed, skipping")

        # Mark setup complete
        if success:
            self.mark_setup_complete()
            print("\n" + "="*60)
            print("  ✅ SETUP COMPLETE!")
            print("="*60)
            print("\nThe application will now start normally.\n")
        else:
            print("\n" + "="*60)
            print("  ⚠️  SETUP COMPLETED WITH WARNINGS")
            print("="*60)
            print("\nSome components may not work correctly.")
            print("Check the messages above for details.\n")

        return success


def check_and_run_setup(
    model_url: Optional[str] = None,
    model_sha256: Optional[str] = None,
    config: Optional[dict] = None
) -> bool:
    """
    Convenience function to check if setup is needed and run it.

    Args:
        model_url: Optional URL to download model from
        model_sha256: Optional SHA256 checksum for model verification
        config: Optional configuration dict with paths

    Returns:
        True if setup not needed or completed successfully
    """
    setup = FirstRunSetup(config=config)

    if not setup.is_first_run():
        # Setup already complete
        return True

    # Run setup
    return setup.run_setup(model_url, model_sha256)