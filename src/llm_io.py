import os
import sys
import json
import pandas as pd
from llama_cpp import Llama
from src.utils import load_pdf_json, course_to_json_path
from src.resource_utils import get_resource_path

# Hardware/Computing Parameters
N_CTX        = int(os.environ.get("N_CTX", 32768)) # Change this for laptops?
N_THREADS    = int(os.environ.get("N_THREADS", max(1, (os.cpu_count() or 2) - 1)))
N_GPU_LAYERS = int(os.environ.get("N_GPU_LAYERS", 0)) # All CPU for now?

# LLM Parameters
MAX_TOKENS = min(int(os.environ.get("MAX_TOKENS", 4096)), 4096)
TEMP       = float(os.environ.get("LLM_TEMP", "0.4"))
TOP_P      = float(os.environ.get("TOP_P", 0.7))
REPEAT_PEN = float(os.environ.get("REPEAT_PEN", 1.3))
MIN_P      = float(os.environ.get("MIN_P", 0.05))


def load_system_prompt(llm_dir):
    """
    Load system prompt from bundled resources.

    Args:
        llm_dir: Relative path to LLM directory (e.g., './configuration/LLM')

    Returns:
        System prompt string or None if not found
    """
    # Build relative path for get_resource_path
    if llm_dir.startswith('./'):
        llm_dir = llm_dir[2:]  # Remove leading './'

    system_prompt_path = get_resource_path(os.path.join(llm_dir, "system_prompt.txt"))
    system_prompt = None

    ## Retrieve system_prompt.txt
    try:
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
    except FileNotFoundError:
        print(f"Missing system prompt at {system_prompt_path}", file=sys.stderr)

    return system_prompt

def load_user_prompt(llm_dir, pdf_json):
    """
    Load user prompt from bundled resources and append evaluation data.

    Args:
        llm_dir: Relative path to LLM directory (e.g., './configuration/LLM')
        pdf_json: Parsed PDF JSON containing free response comments

    Returns:
        User prompt string or None if not found
    """
    # Build relative path for get_resource_path
    if llm_dir.startswith('./'):
        llm_dir = llm_dir[2:]  # Remove leading './'

    user_prompt_path = get_resource_path(os.path.join(llm_dir, "user_prompt.txt"))
    user_prompt = None

    try:
        with open(user_prompt_path, "r", encoding="utf-8") as f:
            user_prompt = f.read().strip()
    except FileNotFoundError:
        print(f"Missing user prompt at {user_prompt_path}", file=sys.stderr)
        return None
    
    user_prompt += "\n\nFREE RESPONSE COMMENTS\n"

    # Likes 
    user_prompt += "\nWhat students liked:"
    liked_comments = pdf_json.get('free_response', {}).get('liked', {})
    for comment in liked_comments:
        user_prompt += f"\n- {comment}"

    # Dislikes 
    user_prompt += "\n\nWhat students disliked:"
    disliked_comments = pdf_json.get('free_response', {}).get('disliked', {})
    for comment in disliked_comments:
        user_prompt += f"\n- {comment}"

    # Comments
    user_prompt += "\nComments"
    comments_dict = pdf_json.get('free_response', {}).get('comments', {})
    for comment in comments_dict:
        user_prompt += f"\n{comment}"

    return user_prompt


def run_llm(
        gguf_path,
        selected_scorecard_courses: pd.DataFrame,
        llm_dir,
        config=None,
        log_callback=None
):
    """
    Spins up the LLM & generates an LLM summary for each viable `scorecard_set`

    Args:
        gguf_path (`str`): path to *.gguf* model
        scorecards_to_generate (`List` of (`tuple` of (`dict`, `./path/to/*.json`))): a `scorecard_set`
        llm_dir (`str`): directory containing system/user prompts
        config (`dict`, optional): full application config
        log_callback (`callable`, optional): function to call with log messages
    """

    def log(message):
        """Helper to log both to console and callback"""
        print(message)
        if log_callback:
            log_callback(message)

    # determine whether to use debug placeholder
    debug_replace_llm_with_placeholder = False
    if config is not None:
        debug_replace_llm_with_placeholder = str(
            config.get("scorecard_gen_settings", {}).get("debug_replace_LLM_with_placeholder", "false")
        ).lower() == "true"

    if debug_replace_llm_with_placeholder:
        log("  ⚠️ Placeholders enabled for LLM generation! debug_replace_LLM_with_placeholder is enabled in config!")

        placeholder_text = (
            "Positive Feedback: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nunc sit amet tempor lacus, sagittis varius elit. Cras dictum tellus in nulla interdum, et congue diam iaculis. Proin in bibendum dui. Mauris sit amet sagittis sapien, et volutpat urna. Nulla in nisi ac urna commodo.\n\n\\par\n"
            "Negative Feedback: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nunc sit amet tempor lacus, sagittis varius elit. Cras dictum tellus in nulla interdum, et congue diam iaculis. Proin in bibendum dui. Mauris sit amet sagittis sapien, et volutpat urna. Nulla in nisi ac urna commodo.\n\n\\par\n"
            "Overall Tone: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nunc sit amet tempor lacus, sagittis varius elit. Cras dictum tellus in nulla interdum, et congue diam iaculis. Proin in bibendum dui. Mauris sit amet sagittis sapien, et volutpat urna. Nulla in nisi ac urna commodo."
        )
        for _, course in selected_scorecard_courses.iterrows():
            pdf_json_path = course_to_json_path(course=course,config=config)
            pdf_json = load_pdf_json(pdf_json_path)

            pdf_json["llm_summary"] = placeholder_text

            with open(pdf_json_path, "w", encoding="utf-8") as out_f:
                json.dump(pdf_json, out_f, indent=4)

            log(f"  🟧 Placeholder LLM summary generated for: {pdf_json_path}")

        return

    # normal behavior below
    if not os.path.exists(gguf_path):
        log(f"❌ GGUF model not found at {gguf_path}. Skipping LLM analysis.")
        return

    # Retrieve system prompt
    log("📝 Loading system prompt...")
    system_prompt = load_system_prompt(llm_dir)

    if not system_prompt:
        log("❌ Could not load system prompts, skipping LLM analysis")
        return

    ## Instantiate LLM
    log("🤖 Initializing language model...")
    try:
        # Instance creation
        llm = Llama(
            model_path=gguf_path,
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_gpu_layers=N_GPU_LAYERS,
            chat_format="llama-3",
            verbose=False,
            min_p = MIN_P,
        )
        log("✅ Language model loaded successfully")
    except Exception as e:
        log(f"❌ Error instantiating the model: {e}")
        return
    
    total_courses = len(selected_scorecard_courses)
    print(selected_scorecard_courses)
    for idx, (_, course) in enumerate(selected_scorecard_courses.iterrows(), 1):
        pdf_json_path = course_to_json_path(course)
        pdf_json = load_pdf_json(pdf_json_path)

        course_name = f"{course.get('Subject', '')} {course.get('Catalog Nbr', '')} {course.get('Term', '')} {course.get('Year', '')}"
        log(f"\n📚 Processing course {idx}/{total_courses}: {course_name}")

        # Retrieve user prompt (contains likes, dislikes, comments etc.)
        log("  📄 Loading evaluation comments...")
        user_prompt = load_user_prompt(llm_dir, pdf_json)
        if not user_prompt:
            log("  ❌ Could not load user prompt, skipping LLM analysis")
            return

        # Messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
        try:
            stream = llm.create_chat_completion(
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMP,
                top_p=TOP_P,
                repeat_penalty=REPEAT_PEN,
                min_p=MIN_P,
                stream=True,
            )
            log(f"  ⏳ Generating LLM insights for {course_name}...")
            full_response_text = []
            # Collect LLM output as it is generated
            for chunk in stream:
                # Get content from the 'delta' key in each chunk
                text = chunk["choices"][0]["delta"].get("content", "")
                if text:
                    full_response_text.append(text)
                    # Still print to console for debugging
                    print(text, end="", flush=True)

            print() # print a line after streaming

            llm_response = "".join(full_response_text)
            pdf_json['llm_summary'] = llm_response
            log(f"  ✅ LLM response completed for {course_name}")

            # Write the complete, .json to the temporary directory
            with open(pdf_json_path, "w", encoding="utf-8") as out_f:
                json.dump(pdf_json, out_f, indent=4)
                log(f"  💾 Saved LLM summary to {pdf_json_path}")

        except Exception as e:
            log(f"  ❌ Error occurred during LLM chat completion: {e}")
