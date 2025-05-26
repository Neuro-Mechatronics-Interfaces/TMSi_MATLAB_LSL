# stream_logger.py
import sys
from PyQt5.QtWidgets import QApplication
from nml.gui.StreamLoggerApp import StreamLoggerApp

def main():
    app = QApplication(sys.argv)
    win = StreamLoggerApp()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
