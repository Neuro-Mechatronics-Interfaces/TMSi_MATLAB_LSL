# stream_interactor.py
import sys
from PyQt5.QtWidgets import QApplication
from nml.gui.StreamInteractorApp import StreamInteractorApp

def main():
    app = QApplication(sys.argv)
    win = StreamInteractorApp()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
