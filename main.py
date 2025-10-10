import json
import os
from src import pdf_parser, utils, data_vis, llm_io

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

        # Run LLM IO
        print("Running LLM I/O")
        pdf_json = utils.get_pdf_json(
            parsed_pdf_dir=paths['parsed_pdf_dir'],
            type=settings['comparison_type'],
            department=settings['department'],
            cata_num=settings['cata'],
            sem="Fall",
            year="2011"
            )
        llm_io.run_llm(gguf_path=paths['gguf_path'],
                       pdf_json= pdf_json,
                       llm_dir= paths['llm_prompt_dir'],
                       temp_dir= paths['temp_dir'])
        # TODO: add cleanup function for temp in utils
        
        # TODO:Generate Visuals
        data_vis.generate_data_visualization(settings)

        # TODO: Assemble & Save Scorecard PDF


    except Exception as e:
        print(f"An error has occured in main: {e}")