import json
import os
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

if __name__ == "__main__":
    try:
        CONFIG_PATH = utils.CONFIG_PATH
        print("🖥️ Opening Config GUI")
        config_gui.open_config_editor(CONFIG_PATH)

        # Load config file
        config = utils.load_config()
        paths = config['paths']
        scorecard_settings = config['scorecard_gen_settings']
        data_vis_settings = config['data_vis_settings']
        include_llm_insights = str(scorecard_settings.get("include_LLM_insights", "false")).lower() == "true"
        overwrite_json = str(config.get("overwrite_settings", {}).get("overwrite_json", "false")).lower() == "true"
        print("✅ Config file loaded")

        utils.verify_directories(config['paths'])

        # Parse Excel
        print("📊 Starting Excel parser")
        overwrite_csv = str(config.get("overwrite_settings", {}).get("overwrite_csv", "false")).lower() == "true"
        csv_path = excel_parser.run_excel_parser(paths['excel_source'], output_dir=paths['csv_dir'], overwrite_csv=overwrite_csv)

        # Clean CSV data
        if (overwrite_csv):
            csv_cleaner.clean_csv(csv_path[0])

        # Parse PDFs
        print("📄 Starting PDF parser")
        pdf_parser.run_pdf_parser(paths['pdf_source'], paths['parsed_pdf_dir'], overwrite_json=overwrite_json)

        # Use CSV/PDF overlap to find viable scorecards
        print("🔗 Finding viable courses for scorecard creation")
        viable_scorecards = data_handler.viable_scorecards(paths['parsed_pdf_dir'],csv_path[0])

        print("🖥️ Opening Scorecard Selection GUI")
        selected_scorecard_courses = select_rows_gui.select_rows_gui(viable_scorecards)
        print(f"  ✅ {len(selected_scorecard_courses)} course(s) selected.")
        
        # Run LLM IO
        if (include_llm_insights):
            print("🤖 Running LLM I/O")
            pdf_json = utils.get_pdf_json(paths['parsed_pdf_dir'], data_vis_settings)
            llm_io.run_llm(gguf_path=paths['gguf_path'],
                        pdf_json= pdf_json,
                        llm_dir= paths['llm_prompt_dir'],
                        temp_dir= paths['temp_dir'])
        
        # TODO: Generate Visuals -- Waiting on CSV changes to integrate
        #data_vis.generate_data_visualization(data_settings, paths['excel_source'])

        # TODO: Assemble & Save Scorecard PDF
        print("📝 Generating LaTeX")
        # Just using the json to populate the latex for now, we will need to include
        #   a csv at some point. Also will want to pivot away from using data vis 
        #       settings from config. Just using for now to illustrate dynamic latex 
        #           generation
        pdf_json_2 = utils.get_pdf_json(paths['parsed_pdf_dir'], data_vis_settings) 
        test_image = "./temporary_files/images/cat_driving_car.jpg"
        scorecard_assembler.assemble_scorecard(
            pdf_json_2,
            test_image,
            tex_output_path=paths['tex_dir'],
            scorecard_output_path=paths['scorecard_dir']
            )

        # TODO: add cleanup function for temp in utils
    except Exception as e:
        print(f"An error has occured in main: {e}")