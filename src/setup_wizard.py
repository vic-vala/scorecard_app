"""
Setup wizard GUI for first-run configuration of ASU Scorecard Generator.

Provides a user-friendly interface for:
- Model download or manual path selection
- LaTeX installation
- Setup progress tracking
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from typing import Optional
from src.first_run_setup import DEFAULT_MODEL_URL, DEFAULT_MODEL_NAME


class SetupWizard:
    """Tkinter-based setup wizard for first-run configuration."""

    def __init__(self, setup_manager):
        """
        Initialize the setup wizard.

        Args:
            setup_manager: FirstRunSetup instance
        """
        self.setup = setup_manager
        self.root = tk.Tk()
        self.root.title("ASU Scorecard Generator - First Run Setup")
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        # State
        self.current_page = 0
        self.model_choice = tk.StringVar(value="download")
        self.model_url = tk.StringVar(value="")
        self.manual_model_path = tk.StringVar(value="")
        self.skip_model = tk.BooleanVar(value=False)

        # Pages
        self.pages = []
        self.create_welcome_page()
        self.create_model_choice_page()
        self.create_model_download_page()
        self.create_latex_install_page()
        self.create_completion_page()

        # Show first page
        self.show_page(0)

    def create_welcome_page(self):
        """Create the welcome/intro page."""
        frame = ttk.Frame(self.root, padding=20)

        # Title
        title = ttk.Label(
            frame,
            text="Welcome to ASU Scorecard Generator",
            font=('Arial', 16, 'bold')
        )
        title.pack(pady=20)

        # Description
        desc = ttk.Label(
            frame,
            text=(
                "This wizard will help you set up the application for first use.\n\n"
                "Setup includes:\n"
                "  • Downloading the LLM model (~5GB)\n"
                "  • Installing LaTeX distribution (~150MB)\n"
                "  • Configuring application settings\n\n"
                "This is a one-time process and may take 10-20 minutes\n"
                "depending on your internet connection.\n\n"
                "You can skip components if needed."
            ),
            justify=tk.LEFT,
            wraplength=600
        )
        desc.pack(pady=20)

        # Continue button
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        continue_btn = ttk.Button(
            btn_frame,
            text="Continue",
            command=lambda: self.show_page(1)
        )
        continue_btn.pack()

        self.pages.append(frame)

    def create_model_choice_page(self):
        """Create page for choosing model download option."""
        frame = ttk.Frame(self.root, padding=20)

        # Title
        title = ttk.Label(
            frame,
            text="LLM Model Setup",
            font=('Arial', 14, 'bold')
        )
        title.pack(pady=10)

        # Description
        desc = ttk.Label(
            frame,
            text=(
                "The application uses a large language model (LLM) to generate\n"
                "insights from course evaluation comments.\n\n"
                "Choose how you want to set up the model:"
            ),
            justify=tk.LEFT
        )
        desc.pack(pady=10)

        # Radio buttons
        radio_frame = ttk.Frame(frame)
        radio_frame.pack(pady=20)

        ttk.Radiobutton(
            radio_frame,
            text="Download model automatically (Recommended, ~5GB)",
            variable=self.model_choice,
            value="download"
        ).pack(anchor=tk.W, pady=5)

        ttk.Radiobutton(
            radio_frame,
            text="I already have a model file",
            variable=self.model_choice,
            value="manual"
        ).pack(anchor=tk.W, pady=5)

        ttk.Radiobutton(
            radio_frame,
            text="Skip model setup (can add later)",
            variable=self.model_choice,
            value="skip"
        ).pack(anchor=tk.W, pady=5)

        # Model URL input (for download option)
        url_frame = ttk.LabelFrame(frame, text="Model Download URL (optional)", padding=10)
        url_frame.pack(pady=10, fill=tk.X)

        ttk.Label(
            url_frame,
            text="If you have a specific model URL, enter it below:"
        ).pack(anchor=tk.W)

        url_entry = ttk.Entry(url_frame, textvariable=self.model_url, width=60)
        url_entry.pack(pady=5, fill=tk.X)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        ttk.Button(
            btn_frame,
            text="Back",
            command=lambda: self.show_page(0)
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Continue",
            command=self.process_model_choice
        ).pack(side=tk.LEFT, padx=5)

        self.pages.append(frame)

    def create_model_download_page(self):
        """Create page for model download progress."""
        frame = ttk.Frame(self.root, padding=20)

        # Title
        title = ttk.Label(
            frame,
            text="Downloading Model",
            font=('Arial', 14, 'bold')
        )
        title.pack(pady=10)

        # Status label
        self.download_status = ttk.Label(
            frame,
            text="Preparing download...",
            justify=tk.CENTER
        )
        self.download_status.pack(pady=10)

        # Progress bar
        self.download_progress = ttk.Progressbar(
            frame,
            length=600,
            mode='determinate'
        )
        self.download_progress.pack(pady=20)

        # Progress text
        self.download_text = ttk.Label(
            frame,
            text="0 MB / 0 MB",
            justify=tk.CENTER
        )
        self.download_text.pack(pady=5)

        # Continue button (disabled until download complete)
        self.download_continue_btn = ttk.Button(
            frame,
            text="Continue",
            command=self.on_download_continue,
            state=tk.DISABLED
        )
        self.download_continue_btn.pack(pady=20)

        self.pages.append(frame)

    def create_latex_install_page(self):
        """Create page for LaTeX installation progress."""
        frame = ttk.Frame(self.root, padding=20)

        # Title
        title = ttk.Label(
            frame,
            text="Installing LaTeX",
            font=('Arial', 14, 'bold')
        )
        title.pack(pady=10)

        # Status label
        self.latex_status = ttk.Label(
            frame,
            text="Preparing installation...",
            justify=tk.CENTER
        )
        self.latex_status.pack(pady=10)

        # Progress bar (indeterminate for LaTeX install)
        self.latex_progress = ttk.Progressbar(
            frame,
            length=600,
            mode='indeterminate'
        )
        self.latex_progress.pack(pady=20)

        # Log text
        log_frame = ttk.LabelFrame(frame, text="Installation Log", padding=10)
        log_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.latex_log = tk.Text(log_frame, height=10, width=70, state=tk.DISABLED)
        self.latex_log.pack(fill=tk.BOTH, expand=True)

        # Scrollbar for log
        scrollbar = ttk.Scrollbar(self.latex_log)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.latex_log.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.latex_log.yview)

        # Continue button (disabled until install complete)
        self.latex_continue_btn = ttk.Button(
            frame,
            text="Continue",
            command=lambda: self.show_page(4),
            state=tk.DISABLED
        )
        self.latex_continue_btn.pack(pady=20)

        self.pages.append(frame)

    def create_completion_page(self):
        """Create the completion/finish page."""
        frame = ttk.Frame(self.root, padding=20)

        # Title
        title = ttk.Label(
            frame,
            text="Setup Complete!",
            font=('Arial', 16, 'bold'),
            foreground='green'
        )
        title.pack(pady=20)

        # Summary
        self.completion_summary = ttk.Label(
            frame,
            text="",
            justify=tk.LEFT,
            wraplength=600
        )
        self.completion_summary.pack(pady=20)

        # Finish button
        finish_btn = ttk.Button(
            frame,
            text="Finish and Launch Application",
            command=self.finish_setup
        )
        finish_btn.pack(pady=20)

        self.pages.append(frame)

    def show_page(self, page_num):
        """Show a specific page of the wizard."""
        # Hide current page
        if self.current_page < len(self.pages):
            self.pages[self.current_page].pack_forget()

        # Show new page
        self.current_page = page_num
        if page_num < len(self.pages):
            self.pages[page_num].pack(fill=tk.BOTH, expand=True)

    def process_model_choice(self):
        """Process the user's model choice and navigate appropriately."""
        choice = self.model_choice.get()

        if choice == "download":
            # Show download page and start download
            self.show_page(2)
            self.start_model_download()
        elif choice == "manual":
            # Ask for model path
            path = filedialog.askopenfilename(
                title="Select GGUF Model File",
                filetypes=[("GGUF Files", "*.gguf"), ("All Files", "*.*")]
            )
            if path:
                self.manual_model_path.set(path)

                # Update config.json with the new model path
                if self.setup.update_config_model_path(path):
                    messagebox.showinfo(
                        "Model Selected",
                        f"Model path set to:\n{path}\n\n"
                        f"Configuration updated successfully.\n\n"
                        f"Proceeding to LaTeX installation."
                    )
                else:
                    messagebox.showwarning(
                        "Configuration Update Failed",
                        f"Model path selected but config update failed.\n"
                        f"You may need to manually update the config later.\n\n"
                        f"Proceeding to LaTeX installation."
                    )

                self.show_page(3)
                self.start_latex_install()
            else:
                messagebox.showwarning("No Model Selected", "Please select a model file or choose a different option.")
        elif choice == "skip":
            # Skip model, go to LaTeX
            messagebox.showinfo(
                "Model Skipped",
                "Model setup skipped. You can add a model later by placing a GGUF file at:\n"
                f"{self.setup.model_path}"
            )
            self.show_page(3)
            self.start_latex_install()

    def start_model_download(self):
        """Start model download in background thread."""
        url = self.model_url.get().strip()

        if not url:
            # Use default URL
            url = DEFAULT_MODEL_URL
            messagebox.showinfo(
                "Using Default Model",
                f"No URL provided. Using default model:\n{DEFAULT_MODEL_NAME}\n\n"
                f"This is Meta-Llama-3.1-8B-Instruct (Q4_K_M quantization, ~5GB)."
            )

        def download_thread():
            def progress_callback(current, total):
                # Update UI from download thread
                progress_percent = (current / total * 100) if total > 0 else 0
                self.root.after(0, lambda: self.update_download_progress(current, total, progress_percent))

            success = self.setup.download_model(url, progress_callback=progress_callback)

            # Update UI on completion
            self.root.after(0, lambda: self.on_download_complete(success))

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

        self.download_status.config(text="Downloading model...")
        self.download_progress.start()

    def update_download_progress(self, current, total, percent):
        """Update download progress bar and text."""
        self.download_progress['value'] = percent
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        self.download_text.config(text=f"{current_mb:.1f} MB / {total_mb:.1f} MB ({percent:.1f}%)")

    def on_download_complete(self, success):
        """Handle download completion."""
        self.download_progress.stop()

        if success:
            self.download_status.config(text="✅ Download complete!")
            self.download_continue_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Success", "Model downloaded successfully!")
        else:
            self.download_status.config(text="❌ Download failed")
            messagebox.showerror(
                "Download Failed",
                "Model download failed. You can try again later or add a model manually."
            )
            self.download_continue_btn.config(state=tk.NORMAL)

    def on_download_continue(self):
        """Handle continue button after download completion."""
        self.show_page(3)
        self.start_latex_install()

    def start_latex_install(self):
        """Start LaTeX installation in background thread."""
        def install_thread():
            self.root.after(0, lambda: self.latex_progress.start())
            self.root.after(0, lambda: self.add_latex_log("Starting TinyTeX installation...\n"))

            # Define callback to update GUI with installation progress
            def log_callback(message):
                # Schedule GUI update on main thread
                self.root.after(0, lambda msg=message: self.add_latex_log(msg + "\n"))

            success = self.setup.install_tinytex(log_callback=log_callback)

            self.root.after(0, lambda: self.on_latex_complete(success))

        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()

        self.latex_status.config(text="Installing TinyTeX...")

    def add_latex_log(self, text):
        """Add text to LaTeX installation log."""
        self.latex_log.config(state=tk.NORMAL)
        self.latex_log.insert(tk.END, text)
        self.latex_log.see(tk.END)
        self.latex_log.config(state=tk.DISABLED)

    def on_latex_complete(self, success):
        """Handle LaTeX installation completion."""
        self.latex_progress.stop()

        if success:
            self.latex_status.config(text="✅ LaTeX installation complete!")
            self.add_latex_log("\n✅ Installation complete!\n")
            self.latex_continue_btn.config(state=tk.NORMAL)
        else:
            self.latex_status.config(text="⚠️ LaTeX installation had issues")
            self.add_latex_log("\n⚠️ Installation completed with warnings.\n")
            self.latex_continue_btn.config(state=tk.NORMAL)
            messagebox.showwarning(
                "Installation Warning",
                "LaTeX installation had some issues. You may need to install LaTeX manually."
            )

    def finish_setup(self):
        """Finish setup and close wizard."""
        # Mark setup complete
        self.setup.mark_setup_complete()

        # Update completion summary
        summary_lines = ["Setup completed successfully!\n\n"]

        if self.setup.model_exists():
            summary_lines.append(f"✅ Model: {self.setup.model_path}\n")
        else:
            summary_lines.append(f"⚠️ Model: Not configured\n")

        if self.setup.tinytex_exists():
            summary_lines.append(f"✅ LaTeX: Installed\n")
        else:
            summary_lines.append(f"⚠️ LaTeX: Not installed\n")

        self.completion_summary.config(text="".join(summary_lines))

        # Close wizard
        messagebox.showinfo("Setup Complete", "The application will now start.")
        self.root.quit()
        self.root.destroy()

    def run(self):
        """Run the wizard (blocking call)."""
        self.root.mainloop()


def run_setup_wizard(setup_manager) -> bool:
    """
    Run the setup wizard GUI.

    Args:
        setup_manager: FirstRunSetup instance

    Returns:
        True if setup completed successfully
    """
    wizard = SetupWizard(setup_manager)
    wizard.run()
    return not setup_manager.is_first_run()
