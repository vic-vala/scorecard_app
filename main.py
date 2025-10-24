import json
import os
from src import pdf_parser, utils, data_vis, llm_io

if __name__ == "__main__":
    try:
        # Load config file
        config = utils.load_config()
        paths = config['paths']
        scorecard_settings = config['scorecard_gen_settings']
        data_settings = config['data_vis_settings']
        include_llm_insights = str(scorecard_settings.get("include_LLM_insights", "false")).lower() == "true"
        overwrite_json = str(config.get("overwrite_settings", {}).get("overwrite_json", "false")).lower() == "true"
        print("✅ Config file loaded")

        utils.verify_directories(config['paths'])

        # TODO: Parse excel sheet(s)

        # Parse PDFs
        print("📄 Starting PDF parser")
        pdf_parser.run_pdf_parser(paths['pdf_source'], paths['parsed_pdf_dir'], overwrite_json=overwrite_json)

        # Run LLM IO
        if (include_llm_insights):
            print("🤖 Running LLM I/O")
            pdf_json = utils.get_pdf_json(
                parsed_pdf_dir=paths['parsed_pdf_dir'],
                type=data_settings['comparison_type'],
                department=data_settings['department'],
                cata_num=data_settings['cata'],
                sem=data_settings['sem'],
                year=data_settings['year']
                )
            llm_io.run_llm(gguf_path=paths['gguf_path'],
                        pdf_json= pdf_json,
                        llm_dir= paths['llm_prompt_dir'],
                        temp_dir= paths['temp_dir'])
        # TODO: add cleanup function for temp in utils
        
        # TODO:Generate Visuals
        data_vis.generate_data_visualization(data_settings, paths['excel_source'])

        # TODO: Assemble & Save Scorecard PDF


    except Exception as e:
        print(f"An error has occured in main: {e}")