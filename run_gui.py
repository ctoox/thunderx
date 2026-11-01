"""ThunderX GUI Launcher"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thunderx.ui.gui import main

if __name__ == "__main__":
    main()
