import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

import asyncio
import qasync
from PySide6.QtWidgets import QApplication
from src.gui.main_window import ContactManagerWindow
from rapidfuzz import fuzz

def main():
    app = QApplication(sys.argv)
    
    # Create the qasync loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create and show main window
    window = ContactManagerWindow()
    window.show()

    # Run the event loop
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main() 