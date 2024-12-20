import sys
import asyncio
import qasync
from PySide6.QtWidgets import QApplication
from src.gui.main_window import ContactManagerWindow

def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = ContactManagerWindow()
    window.show()
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main() 