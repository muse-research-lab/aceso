#!/usr/bin/env bash
set -e

# 0. Install Python 3 (with pip and venv) if it is missing
if [ "$(uname -s)" = "Darwin" ]; then
    command -v python3 >/dev/null 2>&1 || brew install python
else
    python3 -c "import venv, ensurepip" >/dev/null 2>&1 || \
        { sudo apt update && sudo apt install -y python3 python3-pip python3-venv; }
fi
echo "Using $(python3 --version)"

# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate

# 3. Upgrade pip and install requirements
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Setup Complete! ==="
echo "To run the pipeline:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run all experiments: cd Simulator/scripts && ./runner.sh"
echo "  3. Plot results: cd "$(git rev-parse --show-toplevel)" && python3 plotter.py"
echo "  4. Compare plots with the respective paper figures (in the ~/plots folder)."