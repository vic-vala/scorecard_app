import tkinter as tk
from tkinter import ttk
import threading
import time

class LLMLoadingGUI:
    def __init__(self, selected_courses_count: int, selected_instructors_count: int):
        self.selected_courses_count = selected_courses_count
        self.selected_instructors_count = selected_instructors_count
        self.is_running = False
        self.llm_insights = {}

    def show(self):
        """Show the loading GUI and wait for completion."""
        self.window = tk.Tk()
        self.window.title("ASU Scorecard Generator - LLM Processing")
        self.window.geometry("700x500")
        self.window.resizable(False, False)

        self.create_ui()
        self.start_processing()
        self.window.mainloop()

        return self.llm_insights

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
            text="Initializing language model...",
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

        self.llm_log = tk.Text(log_frame, height=12, width=70, state=tk.DISABLED)
        self.llm_log.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.llm_log)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.llm_log.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.llm_log.yview)

        # Continue button
        self.continue_btn = ttk.Button(
            frame,
            text="Continue",
            command=self.on_complete,
            state=tk.DISABLED
        )
        self.continue_btn.pack(pady=20)

    def start_processing(self):
        """Start LLM processing."""
        self.is_running = True
        self.llm_progress.start()

        thread = threading.Thread(target=self._process, daemon=True)
        thread.start()

    def _process(self):
        """Simulate processing."""
        steps = [
            ("Analyzing course evaluation patterns...", 2),
            ("Identifying common feedback themes...", 2),
            ("Processing student response data...", 1),
            ("Generating professor insights...", 2),
            ("Compiling executive summaries...", 1),
        ]

        for step, delay in steps:
            if not self.is_running:
                break
            self._update_status(step)
            time.sleep(delay)

        self._update_status("✅ LLM processing complete!")
        self.continue_btn.config(state=tk.NORMAL)
        self.llm_progress.stop()

    def _update_status(self, message):
        """Update status from thread."""
        self.window.after(0, lambda: self.llm_status.config(text=message))
        self.window.after(0, lambda: self._add_log(message))

    def _add_log(self, message):
        """Add to log."""
        self.llm_log.config(state=tk.NORMAL)
        self.llm_log.insert(tk.END, f"{message}\n")
        self.llm_log.see(tk.END)
        self.llm_log.config(state=tk.DISABLED)

    def on_complete(self):
        """Handle completion."""
        self.is_running = False
        self.window.quit()
        self.window.destroy()
