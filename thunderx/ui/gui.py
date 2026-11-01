"""GUI Application Entry Point"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from .main_window import MainWindow
from .styles import MAIN_STYLE
from ..utils.logger import setup_logger

logger = setup_logger("gui")


class GUI:
    """ThunderX GUI Application"""

    def __init__(self):
        self.app = None
        self.window = None

    def run(self):
        """Run the GUI application"""
        # Create application
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("ThunderX")
        self.app.setApplicationDisplayName("ThunderX Download Manager")
        self.app.setStyle("Fusion")

        # Apply stylesheet
        self.app.setStyleSheet(MAIN_STYLE)

        # Create and show main window
        self.window = MainWindow()
        self.window.show()

        logger.info("GUI application started")

        # Run event loop
        sys.exit(self.app.exec())


def main():
    """Main entry point for GUI"""
    gui = GUI()
    gui.run()


if __name__ == "__main__":
    main()
