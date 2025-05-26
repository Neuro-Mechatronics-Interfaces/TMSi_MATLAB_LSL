import sys
from PyQt5.QtWidgets import QApplication
from nml.gui.MetadataLoggerApp import MetadataLoggerApp

def main():
    app = QApplication(sys.argv)
    window = MetadataLoggerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
