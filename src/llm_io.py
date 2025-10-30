import os
import sys
import json
from llama_cpp import Llama

# Hardware/Computing Parameters
N_CTX        = int(os.environ.get("N_CTX", 32768)) # Change this for laptops?
N_THREADS    = int(os.environ.get("N_THREADS", max(1, (os.cpu_count() or 2) - 1)))
N_GPU_LAYERS = int(os.environ.get("N_GPU_LAYERS", 0)) # All CPU for now?

# LLM Parameters
MAX_TOKENS = min(int(os.environ.get("MAX_TOKENS", 500)), 500)
TEMP       = float(os.environ.get("LLM_TEMP", "0.7"))
TOP_P      = float(os.environ.get("TOP_P", 0.95))
REPEAT_PEN = float(os.environ.get("REPEAT_PEN", 1.1))


def load_system_prompt(llm_dir):
    system_prompt_path = os.path.join(llm_dir, "system_prompt.txt")
    system_prompt = None
    
    ## Retrieve system_prompt.txt
    try:
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
    except FileNotFoundError:
        print(f"Missing system prompt path {system_prompt_path}", file=sys.stderr)

    return system_prompt

def load_user_prompt(llm_dir, pdf_json):
    user_prompt_path = os.path.join(llm_dir, "user_prompt.txt")
    user_prompt = None

    # TODO: Append Free Response Information (definitely better way to do this)
    try:
        with open(user_prompt_path, "r", encoding="utf-8") as f:
            user_prompt = f.read().strip()
    except FileNotFoundError:
        print(f"Missing system prompt path {user_prompt_path}", file=sys.stderr)
    
    user_prompt += "\n\nFREE RESPONSE COMMENTS\n"

    # Likes TODO: Extract like comments

    # Dislikes TODO: Extract dislike comments

    # Comments
    user_prompt += "\nComments"
    comments_dict = pdf_json.get('free_response', {}).get('comments', {})
    for comment in comments_dict:
        user_prompt += f"\n{comment}"

    return user_prompt


def run_llm(gguf_path, pdf_json, llm_dir, temp_dir):
    if not os.path.exists(gguf_path):
        print(f"GGUF model not found at {gguf_path}. Skipping LLM analysis.", file=sys.stderr)
        return

    # Retrieve system prompt
    system_prompt = load_system_prompt(llm_dir)

    if not system_prompt:
        print("Could not load system prompts, skipping LLM analysis", file=sys.stderr)
        return
    
    ## Instantiate LLM
    try:
        # Instance creation
        llm = Llama(
            model_path=gguf_path,
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_gpu_layers=N_GPU_LAYERS,
            chat_format="llama-3",
            verbose=False,
        )
    except Exception as e:
            print(f"Error running instantiation the model:{e}")
            return
    
    # Retrieve user prompt (contains likes, dislikes, comments etc.)
    user_prompt = load_user_prompt(llm_dir, pdf_json)
    if not user_prompt:
        print("Could not load user prompt, skipping LLM analysis", file=sys.stderr)
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
            stream=True,
        )
        print("Generating LLM response...")
        full_response_text = []
        for chunk in stream:
            # Get content from the 'delta' key in each chunk
            text = chunk["choices"][0]["delta"].get("content", "")
            if text:
                full_response_text.append(text)

        llm_response = "".join(full_response_text)
        pdf_json['llm_summary'] = llm_response
        print("LLM response completed!")

        # Write the complete, .json to the temporary directory
        os.makedirs(os.path.dirname(temp_dir), exist_ok=True)
        temp_path = f"{temp_dir}/temp.json"
        with open(temp_path, "w", encoding="utf-8") as out_f:
            json.dump(pdf_json, out_f, indent=4)
            print(f"LLM summary added to JSON and saved to temporary file: %s" % ("temp"))
            
    except Exception as e:
        print(f"Error occured during LLM chat completion")