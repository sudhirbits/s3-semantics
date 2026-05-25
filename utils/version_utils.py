import os


VERSION = float(os.getenv("MVP_VERSION", "1.0"))
IS_V2_PLUS = VERSION >= 2

print(f"Running with VERSION={VERSION}, IS_V2_PLUS={IS_V2_PLUS}")
