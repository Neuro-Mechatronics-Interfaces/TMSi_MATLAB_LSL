import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer

from pylsl import resolve_streams, StreamInlet

from nml.lsl.BinaryStreamLogger import BinaryStreamLogger


class StreamLoggerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stream Logger")
        self.setGeometry(100, 100, 400, 250)

        self.stream_select = QListWidget()
        self.refresh_btn = QPushButton("Refresh Streams")
        self.dir_btn = QPushButton("Select Log Folder")
        self.toggle_btn = QPushButton("Start Logging")
        self.status = QLabel("Idle")
        self.status.setAlignment(Qt.AlignCenter)

        self.log_dir = r'logs\streams'
        self.active_loggers = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_all)

        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("Available LSL Streams:"))
        self.layout.addWidget(self.stream_select)
        self.layout.addWidget(self.refresh_btn)
        self.layout.addWidget(self.dir_btn)
        self.layout.addWidget(self.toggle_btn)
        self.layout.addWidget(self.status)
        self.setLayout(self.layout)

        self.refresh_btn.clicked.connect(self.refresh_streams)
        self.dir_btn.clicked.connect(self.select_folder)
        self.toggle_btn.clicked.connect(self.toggle_logging)

        self.refresh_streams()

    def refresh_streams(self):
        self.stream_select.clear()
        self.available = resolve_streams()
        for s in self.available:
            label = f"{s.name()} [{s.type()}]"
            item = QListWidgetItem(label)
            item.setCheckState(Qt.Unchecked)
            self.stream_select.addItem(item)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self.log_dir)
        if folder:
            self.log_dir = folder

    def toggle_logging(self):
        if self.active_loggers:
            # Stop logging
            self.timer.stop()
            for logger in self.active_loggers:
                logger.close()
            self.active_loggers = []
            self.toggle_btn.setText("Start Logging")
            self.status.setText("Logging stopped.")
        else:
            # Start logging
            os.makedirs(self.log_dir, exist_ok=True)
            self.active_loggers = []
            for i in range(self.stream_select.count()):
                item = self.stream_select.item(i)
                if item.checkState() == Qt.Checked:
                    stream = self.available[i]
                    inlet = StreamInlet(stream)
                    fname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{stream.name()}.bin"
                    path = os.path.join(self.log_dir, fname)
                    logger = BinaryStreamLogger(inlet, path)
                    self.active_loggers.append(logger)
            self.timer.start(50)
            self.toggle_btn.setText("Stop Logging")
            self.status.setText(f"Logging {len(self.active_loggers)} stream(s)...")

    def poll_all(self):
        for logger in self.active_loggers:
            logger.log_chunk()

    def closeEvent(self, event):
        if self.active_loggers:
            self.toggle_logging()
            event.accept()
