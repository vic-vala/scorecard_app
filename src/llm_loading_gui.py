import tkinter as tk
from tkinter import ttk
import threading

class LLMLoadingGUI:
    def __init__(self, selected_courses_count: int, selected_instructors_count: int):
        self.selected_courses_count = selected_courses_count
        self.selected_instructors_count = selected_instructors_count
        self.is_running = False
        self.processing_complete = False

        # Parameters for LLM processing (set via run_processing)
        self.llm_params = None

    def show(self, gguf_path=None, selected_scorecard_courses=None, llm_dir=None, config=None):
        """
        Show the loading GUI and wait for completion.

        Args:
            gguf_path: Path to GGUF model (if provided, starts processing immediately)
            selected_scorecard_courses: DataFrame of courses to process
            llm_dir: Directory containing LLM prompts
            config: Application config dict
        """
        self.window = tk.Tk()
        self.window.title("ASU Scorecard Generator - LLM Processing")
        self.window.geometry("800x600")
        self.window.resizable(False, False)

        self.create_ui()

        # If parameters provided, start processing immediately after GUI shows
        if gguf_path is not None:
            self.window.after(100, lambda: self.run_processing(
                gguf_path, selected_scorecard_courses, llm_dir, config
            ))

        self.window.mainloop()

    def create_ui(self):
        """Create UI matching setup_wizard style."""
        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            frame,
            text="Generating LLM Insights",
            font=('Arial', 14, 'bold')
        )
        title.pack(pady=10)

        # Description
        desc = ttk.Label(
            frame,
            text=f"Processing {self.selected_courses_count} courses and {self.selected_instructors_count} instructors...",
            justify=tk.CENTER
        )
        desc.pack(pady=10)

        # Status label
        self.llm_status = ttk.Label(
            frame,
            text="Waiting to start...",
            justify=tk.CENTER
        )
        self.llm_status.pack(pady=10)

        # Progress bar
        self.llm_progress = ttk.Progressbar(
            frame,
            length=600,
            mode='indeterminate'
        )
        self.llm_progress.pack(pady=20)

        # Log area
        log_frame = ttk.LabelFrame(frame, text="LLM Processing Log", padding=10)
        log_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.llm_log = tk.Text(log_frame, height=12, width=70, state=tk.DISABLED, wrap=tk.WORD)
        self.llm_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(log_frame, command=self.llm_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.llm_log.config(yscrollcommand=scrollbar.set)

        # Continue button
        self.continue_btn = ttk.Button(
            frame,
            text="Continue",
            command=self.on_complete,
            state=tk.DISABLED
        )
        self.continue_btn.pack(pady=20)

    def run_processing(self, gguf_path, selected_scorecard_courses, llm_dir, config):
        """
        Start LLM processing with actual llm_io.run_llm() function

        Args:
            gguf_path: Path to GGUF model
            selected_scorecard_courses: DataFrame of courses to process
            llm_dir: Directory containing LLM prompts
            config: Application config dict
        """
        self.llm_params = {
            'gguf_path': gguf_path,
            'selected_scorecard_courses': selected_scorecard_courses,
            'llm_dir': llm_dir,
            'config': config
        }

        self.is_running = True
        self.llm_progress.start()
        self._update_status("Starting LLM processing...")

        # Start processing in background thread
        thread = threading.Thread(target=self._process, daemon=True)
        thread.start()

    def _process(self):
        """Run actual LLM processing in background thread."""
        try:
            from src import llm_io

            # Run LLM with callback for logging
            llm_io.run_llm(
                gguf_path=self.llm_params['gguf_path'],
                selected_scorecard_courses=self.llm_params['selected_scorecard_courses'],
                llm_dir=self.llm_params['llm_dir'],
                config=self.llm_params['config'],
                log_callback=self._log_from_thread
            )

            # Processing complete - enable continue button
            self.processing_complete = True
            self._complete_processing("✅ LLM processing complete!")

        except Exception as e:
            error_msg = f"❌ Error during LLM processing: {e}"
            self._update_status(error_msg)
            self._log_from_thread(error_msg)
            self._complete_processing(error_msg)

    def _complete_processing(self, final_message):
        """Mark processing as complete and enable continue button"""
        self.window.after(0, lambda: self._update_status(final_message))
        self.window.after(0, lambda: self.llm_progress.stop())
        self.window.after(0, lambda: self.continue_btn.config(state=tk.NORMAL))
        self._log_from_thread("\n" + "="*60)
        self._log_from_thread("Processing complete! Click 'Continue' to proceed.")
        self._log_from_thread("="*60)

    def _log_from_thread(self, message):
        """Thread-safe logging callback for llm_io.py"""
        self.window.after(0, lambda: self._add_log(message))

    def _update_status(self, message):
        """Update status from thread"""
        self.window.after(0, lambda: self.llm_status.config(text=message))

    def _add_log(self, message):
        """Add to log"""
        self.llm_log.config(state=tk.NORMAL)
        self.llm_log.insert(tk.END, f"{message}\n")
        self.llm_log.see(tk.END)
        self.llm_log.config(state=tk.DISABLED)

    def on_complete(self):
        """Handle completion."""
        self.is_running = False
        self.window.quit()
        self.window.destroy()