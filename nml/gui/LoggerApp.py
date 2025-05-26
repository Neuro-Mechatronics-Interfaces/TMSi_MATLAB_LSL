import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QComboBox, QLineEdit, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from pylsl import resolve_streams, StreamInlet
from nml.lsl.ParameterLogger import ParameterLogger


class LoggerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parameter Logger")
        self.setGeometry(100, 100, 400, 200)

        self.logger = None

        # UI Elements
        self.stream_select = QComboBox()
        self.stream_refresh_btn = QPushButton("Refresh Streams")
        self.filename_input = QLineEdit("logsession")
        self.folder_btn = QPushButton("Select Log Folder")
        self.toggle_btn = QPushButton("Start Logging")
        self.status = QLabel("Idle")
        self.status.setAlignment(Qt.AlignCenter)

        self.log_dir = "logs"
        self.selected_stream_name = None

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Stream to log:"))
        layout.addWidget(self.stream_select)
        layout.addWidget(self.stream_refresh_btn)

        layout.addWidget(QLabel("Base filename suffix:"))
        layout.addWidget(self.filename_input)

        layout.addWidget(self.folder_btn)
        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.status)

        self.setLayout(layout)

        # Bindings
        self.stream_refresh_btn.clicked.connect(self.refresh_streams)
        self.folder_btn.clicked.connect(self.select_folder)
        self.toggle_btn.clicked.connect(self.toggle_logging)

        self.refresh_streams()

    def refresh_streams(self):
        self.stream_select.clear()
        try:
            streams = resolve_streams()
            marker_streams = [s for s in streams if s.type() == "Markers"]
            self.available_streams = marker_streams
            for s in marker_streams:
                self.stream_select.addItem(f"{s.name()} [{s.source_id()}]")
        except Exception as e:
            QMessageBox.critical(self, "Stream Error", f"Failed to resolve streams:\n{e}")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Log Folder", self.log_dir)
        if folder:
            self.log_dir = folder

    def closeEvent(self, event):
        if self.logger:
            self.logger.stop()
        event.accept()


    def toggle_logging(self):
        if self.logger is None:
            # Start logging
            if self.stream_select.currentIndex() == -1:
                QMessageBox.warning(self, "No Stream", "Please select an LSL stream.")
                return

            try:
                stream_info = self.available_streams[self.stream_select.currentIndex()]
                suffix = self.filename_input.text().strip()
                if not suffix:
                    suffix = "log"

                os.makedirs(self.log_dir, exist_ok=True)

                from pylsl import StreamInlet
                self.logger = ParameterLogger(log_dir=self.log_dir)
                self.logger.base_filename += f"_{suffix}"
                self.logger.inlet = StreamInlet(stream_info)
                self.logger.start()

                self.status.setText(f"Logging to: {self.logger.base_filename}")
                self.toggle_btn.setText("Stop Logging")

            except Exception as e:
                QMessageBox.critical(self, "Logging Error", f"Failed to start logging:\n{e}")
                self.logger = None
        else:
            # Stop logging
            try:
                self.logger.stop()
                self.logger = None
                self.status.setText("Logging stopped.")
                self.toggle_btn.setText("Start Logging")
            except Exception as e:
                QMessageBox.critical(self, "Stop Error", f"Failed to stop logger:\n{e}")