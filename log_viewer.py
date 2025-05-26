import sys
from PyQt5.QtWidgets import QApplication
from nml.gui.LogViewer import LogViewer

def main():
    app = QApplication(sys.argv)
    viewer = LogViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
