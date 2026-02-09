import os
import sys
import json
import platform
import pandas as pd
from llama_cpp import Llama
from src.utils import load_pdf_json, course_to_json_path, log_to_file
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


def _detect_gpu_capabilities(log_callback=None):
    """
    Detect available GPU and estimate VRAM for LLM initialization params

    Returns:
        `dict` (GPU information with keys):
            - has_gpu (`bool`): Whether a compatible GPU was detected
            - gpu_type (`str`): 'nvidia', 'amd', 'intel', or 'none'
            - vram_gb (`float`): Estimated VRAM in GB, or 0 if unknown
            - recommended_layers (`int`): Suggested n_gpu_layers for offloading
    """

    def log(message):
        """Helper to log both to console and callback"""
        print(message)
        if log_callback:
            log_callback(message)
        log_to_file(message, log_file="llm.log")

    gpu_info = {
        "has_gpu": False,
        "gpu_type": "none",
        "vram_gb": 0.0,
        "recommended_layers": 0
    }

    # Try NVIDIA GPU detection (CUDA)
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            vram_mb = float(result.stdout.strip().split('\n')[0])
            vram_gb = vram_mb / 1024
            gpu_info["has_gpu"] = True
            gpu_info["gpu_type"] = "nvidia"
            gpu_info["vram_gb"] = vram_gb

            # Estimate layer offloading based on VRAM
            # Rule of thumb: ~4GB for 8B model, can offload more with more VRAM
            if vram_gb >= 8:
                gpu_info["recommended_layers"] = 33  # Full offload for 8B models
            elif vram_gb >= 6:
                gpu_info["recommended_layers"] = 24  # Partial offload
            elif vram_gb >= 4:
                gpu_info["recommended_layers"] = 16  # Limited offload
            else:
                gpu_info["recommended_layers"] = 0   # Too little VRAM

            log(f"  🎮 NVIDIA GPU detected: {vram_gb:.1f}GB VRAM")
            log(f"  💡 Recommended GPU layers: {gpu_info['recommended_layers']}")
            return gpu_info
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass  # nvidia-smi not found or failed

    # Try AMD GPU detection (ROCm)
    try:
        import subprocess
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and "Total" in result.stdout:
            # Parse ROCm output (format varies)
            for line in result.stdout.split('\n'):
                if "Total" in line and "MB" in line:
                    vram_mb = float(line.split()[1])
                    vram_gb = vram_mb / 1024
                    gpu_info["has_gpu"] = True
                    gpu_info["gpu_type"] = "amd"
                    gpu_info["vram_gb"] = vram_gb
                    gpu_info["recommended_layers"] = min(33, int(vram_gb * 4))
                    log(f"  🎮 AMD GPU detected: {vram_gb:.1f}GB VRAM")
                    return gpu_info
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass  # rocm-smi not found or failed

    # Try Intel GPU detection (Level Zero)
    try:
        import subprocess
        result = subprocess.run(
            ["sycl-ls"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and "Intel" in result.stdout:
            gpu_info["has_gpu"] = True
            gpu_info["gpu_type"] = "intel"
            gpu_info["vram_gb"] = 0.0  # Can't easily query Intel iGPU VRAM
            gpu_info["recommended_layers"] = 0  # Conservative for integrated GPUs
            log(f"  🎮 Intel GPU detected (shared memory)")
            log(f"  💡 Intel iGPU support limited - using CPU")
            return gpu_info
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass

    # No GPU detected
    log(f"  💻 No compatible GPU detected - using CPU only")
    return gpu_info


def _configure_llama_cpu_compatibility():
    """
    Configure environment variables for maximum CPU compatibility.
    Prevents illegal instruction errors on Windows and other platforms.

    This function sets conservative CPU instruction flags to avoid crashes
    caused by AVX/AVX2/AVX-512 instruction mismatches between llama-cpp-python
    compilation and runtime CPU capabilities.
    """
    # Disable advanced CPU instructions that may not be supported
    compatibility_flags = {
        "LLAMA_NO_ACCELERATE": "1",      # Disable hardware acceleration fallbacks
        "LLAMA_NO_AVX": "1",             # Disable AVX instructions
        "LLAMA_NO_AVX2": "1",            # Disable AVX2 instructions
        "LLAMA_NO_AVX512": "1",          # Disable AVX-512 instructions
        "LLAMA_NO_FMA": "1",             # Disable FMA instructions
        "LLAMA_NO_F16C": "1",            # Disable F16C instructions
    }

    # Apply flags without overwriting user-set values
    for flag, value in compatibility_flags.items():
        if flag not in os.environ:
            os.environ[flag] = value


def _get_safe_llama_params(log_callback=None, gpu_info=None):
    """
    Returns conservative Llama initialization parameters for maximum compatibility.

    Args:
        log_callback: Optional callback function for logging
        gpu_info: Optional GPU detection results from _detect_gpu_capabilities()

    Returns:
        dict: Safe initialization parameters for Llama()
    """
    def log(message):
        """Helper to log both to console and callback"""
        print(message)
        if log_callback:
            log_callback(message)
        log_to_file(message, log_file="llm.log")

    # Start with CPU-only defaults
    params = {
        "n_gpu_layers": 0,           # CPU-only processing (may be overridden)
        "use_mmap": True,            # Memory-map model file (reduces RAM pressure)
        "use_mlock": False,          # Don't lock pages in RAM (compatibility)
        "verbose": False,            # Suppress llama.cpp debug output
    }

    # Check if GPU offloading is possible and beneficial
    if gpu_info and gpu_info["has_gpu"] and gpu_info["recommended_layers"] > 0:
        # Only use GPU if user hasn't explicitly disabled it via environment
        user_gpu_layers = int(os.environ.get("N_GPU_LAYERS", -1))

        if user_gpu_layers == -1:
            # User hasn't set preference - use detected recommendation
            params["n_gpu_layers"] = gpu_info["recommended_layers"]
            log(f"  🚀 GPU acceleration enabled: {gpu_info['recommended_layers']} layers offloaded")
        elif user_gpu_layers == 0:
            # User explicitly disabled GPU
            log(f"  ⚙️ GPU available but disabled via N_GPU_LAYERS=0")
        else:
            # User set custom value
            params["n_gpu_layers"] = user_gpu_layers
            log(f"  ⚙️ Using custom GPU layers: {user_gpu_layers}")
    else:
        log(f"  💻 Using CPU-only mode")

    # Platform-specific adjustments
    system = platform.system()

    if system == "Windows":
        # Windows-specific safety measures
        params["low_vram"] = True    # Enable low-VRAM mode for stability
        log("  🪟 Windows detected: Applying conservative memory settings")
    elif system == "Linux":
        params["use_mlock"] = False
        log("  🐧 Linux detected: Using standard compatibility settings")

    return params


def _load_llm_model(gguf_path, log_callback=None):
    """
    Load LLM model with progressive fallback strategies.

    Attempts to load the model with increasingly conservative settings
    if initial attempts fail due to CPU instruction incompatibilities.

    Args:
        gguf_path (str): Path to GGUF model file
        log_callback (callable): Optional logging callback

    Returns:
        Llama: Loaded model instance, or None if all attempts fail
    """
    def log(message):
        """Helper to log both to console and callback"""
        print(message)
        if log_callback:
            log_callback(message)
        log_to_file(message, log_file="llm.log")

    # Detect GPU capabilities first
    log("  🔍 Detecting GPU capabilities...")
    gpu_info = _detect_gpu_capabilities(log_callback)

    # Pre-configure CPU compatibility flags (only disable if no GPU or GPU disabled)
    if not gpu_info["has_gpu"] or gpu_info["recommended_layers"] == 0:
        _configure_llama_cpu_compatibility()

    # Strategy 1: Optimal settings (GPU if available, otherwise conservative CPU)
    if gpu_info["has_gpu"] and gpu_info["recommended_layers"] > 0:
        log(f"  🔧 Attempting to load model with GPU acceleration ({gpu_info['gpu_type'].upper()})...")
    else:
        log("  🔧 Attempting to load model with conservative CPU settings...")

    try:
        safe_params = _get_safe_llama_params(log_callback, gpu_info)
        llm = Llama(
            model_path=gguf_path,
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            chat_format="llama-3",
            min_p=MIN_P,
            **safe_params
        )
        if gpu_info["has_gpu"] and safe_params["n_gpu_layers"] > 0:
            log(f"  ✅ Model loaded successfully with GPU acceleration ({safe_params['n_gpu_layers']} layers)")
        else:
            log("  ✅ Model loaded successfully with CPU")
        return llm
    except Exception as e:
        error_msg = str(e)
        log(f"  ⚠️ Initial load failed: {error_msg}")

        # Check for specific illegal instruction error
        if "0xc000001d" in error_msg or "illegal instruction" in error_msg.lower():
            log("  🔍 Detected illegal instruction error - CPU compatibility issue")
            log("  💡 This usually means llama-cpp-python was compiled with")
            log("     instructions your CPU doesn't support (AVX2/AVX-512)")

    # Strategy 2: Force CPU-only with reduced context window
    log("  🔧 Attempting CPU fallback with reduced context window...")
    _configure_llama_cpu_compatibility()  # Ensure CPU flags are set
    try:
        safe_params = _get_safe_llama_params(log_callback)  # No GPU info = CPU only
        safe_params["n_gpu_layers"] = 0  # Force CPU
        llm = Llama(
            model_path=gguf_path,
            n_ctx=min(N_CTX, 8192),  # Reduce context to 8K
            n_threads=max(1, N_THREADS // 2),  # Use fewer threads
            chat_format="llama-3",
            min_p=MIN_P,
            **safe_params
        )
        log("  ⚠️ Model loaded with reduced context window (8K tokens, CPU only)")
        return llm
    except Exception as e:
        log(f"  ⚠️ Reduced context fallback failed: {e}")

    # Strategy 3: Ultra-minimal configuration
    log("  🔧 Attempting ultra-minimal configuration...")
    try:
        llm = Llama(
            model_path=gguf_path,
            n_ctx=2048,              # Minimal context
            n_threads=1,             # Single thread
            n_gpu_layers=0,
            use_mmap=False,          # Disable memory mapping
            use_mlock=False,
            verbose=False,
            chat_format="llama-3"
        )
        log("  ⚠️ Model loaded with ultra-minimal settings (2K context, single-threaded)")
        return llm
    except Exception as e:
        log(f"  ⚠️ Ultra-minimal configuration failed: {e}")

    # All strategies failed
    log("  ❌ All loading strategies failed")
    log("  💡 Possible solutions:")
    log("     1. Reinstall llama-cpp-python: pip uninstall llama-cpp-python && pip install llama-cpp-python --no-cache-dir")
    log("     2. Use prebuilt wheels: pip install llama-cpp-python --prefer-binary")
    log("     3. Build from source with CPU-specific flags:")
    log("        CMAKE_ARGS=\"-DLLAMA_AVX2=OFF -DLLAMA_AVX=OFF\" pip install llama-cpp-python --force-reinstall")
    log("     4. Enable debug placeholder mode in config.json")

    return None


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

    ## Instantiate LLM with progressive fallback strategies
    log("🤖 Initializing language model...")
    llm = _load_llm_model(gguf_path, log_callback=log_callback)

    if llm is None:
        log("❌ Failed to load language model after all fallback attempts")
        return
    
    total_courses = len(selected_scorecard_courses)
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
