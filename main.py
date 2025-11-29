import json
import os
from pathlib import Path
import pandas as pd

# Fix matplotlib font cache for frozen apps (prevents slow startup)
os.environ['MPLCONFIGDIR'] = str(Path.home() / '.matplotlib')

from src import (
    pdf_parser,
    utils,
    data_vis,
    llm_io,
    excel_parser,
    scorecard_assembler,
    csv_cleaner,
    config_gui,
    data_handler,
    select_rows_gui,
)

class Application:

    def __init__(self, config):
        """
        Initialize fields reused through the application lifetime
        """
        self.config = config
        self.paths = config['paths']
        self.sc_settings = config['scorecard_gen_settings']
        self.data_vis_settings = config['data_vis_settings']
        self.include_llm_insights = str(self.sc_settings.get("include_LLM_insights", "false")).lower() == "true"
        self.overwrite_json = str(config.get("overwrite_settings", {}).get("overwrite_json", "false")).lower() == "true"

        # Set later
        self.overwrite_csv: bool
        self.csv_path = None
        self.viable_scorecards: pd.DataFrame
        self.selected_scorecard_courses: pd.DataFrame
        self.selected_history_courses: pd.DataFrame
        self.selected_scorecard_instructors: pd.DataFrame
        print("✅ Config file loaded")

    def parse_excel(self):
        print("📊 Starting Excel parser")
        self.overwrite_csv = str(self.config.get("overwrite_settings", {}).get("overwrite_csv", "false")).lower() == "true"
        self.csv_path = excel_parser.run_excel_parser(self.paths['excel_source'], output_dir=self.paths['csv_dir'], overwrite_csv=self.overwrite_csv)

        # Clean CSV data
        if (self.overwrite_csv):
            csv_cleaner.clean_csv(self.csv_path[0])

    def parse_pdfs(self):
        print("📄 Starting PDF parser")
        pdf_parser.run_pdf_parser(self.paths['pdf_source'], self.paths['parsed_pdf_dir'], overwrite_json=self.overwrite_json)

    def find_viable_scorecards(self):
        print("🔗 Finding viable courses for scorecard creation")
        self.viable_scorecards = data_handler.viable_scorecards(self.paths['parsed_pdf_dir'], self.csv_path[0])

    def selection_gui(self):
        unique_courses = data_handler.get_unique_courses(self.csv_path[0])
        instructors = data_handler.get_instructors(self.csv_path[0])

        print("🖥️ Opening Selection GUI (Sessions / Courses / Instructors)")
        (
            self.selected_scorecard_courses,
            self.selected_history_courses,
            self.selected_scorecard_instructors,
        ) = select_rows_gui.select_rows_gui_with_tabs(
            self.viable_scorecards,
            unique_courses,
            instructors,
        )

        print(f"  ✅ {len(self.selected_scorecard_courses)} course session(s) selected.")
        print(f"  ✅ {len(self.selected_history_courses)} course(s) selected for history graphs.")
        print(f"  ✅ {len(self.selected_scorecard_instructors)} instructor(s) selected.")
    
    def gather_llm_insights(self):
        """
        Populate LLM insight fields for viable scorecards.
        A viable scorecard has a matching `csv_row` and existing
        `./path/to/parsed_pdf.json`.
        """

        if (self.include_llm_insights):
            print("🤖 Running LLM I/O")

            from src.llm_loading_gui import LLMLoadingGUI

            selected_courses = len(self.selected_scorecard_courses)
            selected_instructors = len(self.selected_scorecard_instructors)

            # Create and show GUI with processing parameters
            llm_gui = LLMLoadingGUI(selected_courses, selected_instructors)
            llm_gui.show(
                gguf_path=self.paths['gguf_path'],
                selected_scorecard_courses=self.selected_scorecard_courses,
                llm_dir=self.paths['llm_prompt_dir'],
                config=self.config
            )

            print(" ✅ LLM Tasks Completed")


    def generate_data_visualizations(self):
        print("📈 Generating Data Visualizations")
        data_vis.generate_data_visualization(
            self.config, 
            self.selected_scorecard_courses, 
            self.selected_scorecard_instructors, 
            self.csv_path[0], 
            self.selected_history_courses)
        
    def create_scorecards(self):
        print("📝 Generating LaTeX")

        # Iterate through the scorecards to generate one at a time
        for _, course in self.selected_scorecard_courses.iterrows():
            scorecard_assembler.assemble_scorecard(
                course=course, 
                config=self.config,
                csv_path=self.csv_path[0],
            )
        
        for _, instructor in self.selected_scorecard_instructors.iterrows():
            scorecard_assembler.assemble_instructor_scorecard(
                instructor=instructor,
                config=self.config,
                csv_path=self.csv_path[0],
            )

if __name__ == "__main__":
    try:
        # Load config early to setup default directories 
        config = utils.load_config()
        utils.verify_directories(config['paths'])

        # First-run setup check for gguf, TinyTex, and ./resources/.setup_complete flag
        from src.first_run_setup import FirstRunSetup, DEFAULT_MODEL_URL
        from src.setup_wizard import run_setup_wizard

        setup = FirstRunSetup(config=config)

        if setup.is_first_run():
            print("\n" + "="*60)
            print("  FIRST RUN DETECTED - Starting Setup Wizard")
            print("="*60 + "\n")

            # Run setup wizard GUI
            run_setup_wizard(setup)

            print("\n✅ Setup complete. Starting application...\n")

        # Add TinyTeX to PATH (needed for pdflatex)
        setup.add_tinytex_to_path()

        # Config GUI
        CONFIG_PATH = utils.CONFIG_PATH
        print("🖥️ Opening Config GUI")
        config_gui.open_config_editor(CONFIG_PATH)

        # Reload config after GUI (in case user modified it)
        config = utils.load_config()

        # Application object to logically organize tasks
        app = Application(config=config)
        app.parse_excel()
        app.parse_pdfs()

        # Use CSV/PDF overlap to find viable scorecards
        app.find_viable_scorecards()

        app.selection_gui()
        app.gather_llm_insights()
        app.generate_data_visualizations()
        app.create_scorecards()

        # TODO: add cleanup function for temp in utils
    except Exception as e:
        print(f"An error has occured in main: {e}")
