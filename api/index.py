import os
import sys

# Ensure backend and root directories are in python module search path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
backend_path = os.path.join(root_dir, "backend")

for path in (backend_path, root_dir, current_dir):
    if path and path not in sys.path:
        sys.path.insert(0, path)

from main import app
