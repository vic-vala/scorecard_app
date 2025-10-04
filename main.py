import json
import os
from src import pdf_parser, utils, data_vis

if __name__ == "__main__":
    try:
        # Load config file
        config = utils.load_config()
        print("Loaded config")

        paths = config['paths']
        settings = config['scorecard_gen_settings']
        print("Config file loaded")

        utils.verify_directories(config['paths'])

        # Parse PDFs
        print("Starting PDF parser")
        pdf_parser.run_pdf_parser(paths['pdf_source'], paths['parsed_pdf_dir'])

        # Generate Visuals
        data_vis.generate_data_visualization(settings)

        # Assemble & Save Scorecard PDF
    except Exception as e:
        print(f"An error has occured: {e}")