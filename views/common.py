import streamlit as st
import time
import functools
import logging
import sys

logger = logging.getLogger("task_classifier")

# Configure only once to avoid duplicate logs on rerun
if not logger.handlers:
    logger.setLevel(logging.INFO)

    # Console Handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    # Format: Time | Level | Component | Message
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

def get_logger(component_name: str):
    """Returns a logger adapter with the component name pre-filled"""
    return logging.getLogger(f"task_classifier.{component_name}")

# --- CSS Styling ---
def inject_custom_css():
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
            h4 { font-size: 1.1rem !important; margin-bottom: 0.2rem !important; }
            .ai-hint { font-size: 0.9rem; color: #888; font-style: italic; margin-bottom: 1rem; }
            .dest-project { font-size: 1.3rem; font-weight: bold; color: #4DA6FF; margin-bottom: 0.5rem; }

            /* Card Styling */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #1E1E1E;
                border-radius: 12px;
                padding: 1rem;
            }

            /* Button Hacks */
            button:has(p:contains("Add")) { background-color: #28a745 !important; border-color: #28a745 !important; }
            button:has(p:contains("Skip")) { background-color: #007bff !important; border-color: #007bff !important; }
        </style>
    """, unsafe_allow_html=True)

# --- DEBUG LOGGING UTILITY ---
def log_action(action: str, details: str):
    logger.info(f"ACTION: {action} - {details}")

def log_state(label: str, data):
    logger.debug(f"STATE: {label} - {data}")

def debug_log(func):
    """Decorator to print function calls, args, and execution time to stdout."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        arg_str = ", ".join([repr(a) for a in args])
        kwarg_str = ", ".join([f"{k}={v!r}" for k, v in kwargs.items()])
        all_args = ", ".join(filter(None, [arg_str, kwarg_str]))
        if len(all_args) > 100: all_args = all_args[:97] + "..."

        print(f"➡️  CALL: {func.__name__}({all_args})")
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.time() - start_time) * 1000
            res_str = repr(result)
            if len(res_str) > 100: res_str = res_str[:97] + "..."
            print(f"✅  RETURN: {func.__name__} in {elapsed:.2f}ms -> {res_str}")
            return result
        except Exception as e:
            print(f"❌  ERROR in {func.__name__}: {str(e)}")
            raise e
    return wrapper