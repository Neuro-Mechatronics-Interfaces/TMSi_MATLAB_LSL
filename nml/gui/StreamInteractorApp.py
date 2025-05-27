import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QFileDialog, QHBoxLayout, QComboBox, QDialog,
    QDialogButtonBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer
from pylsl import resolve_streams, StreamInlet

from nml.lsl.BinaryStreamLogger import BinaryStreamLogger
from nml.plot.TimeSeriesPlot import TimeSeriesPlot
from nml.plot.TimeSeriesArray import TimeSeriesArray


class StreamInteractorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stream Interactor")
        self.setGeometry(100, 100, 1000, 600)

        # --- State
        self.available = []
        self.connected_loggers = []
        self.active_loggers = []
        self.plot_widgets = []

        # --- Top: Stream Selection
        self.stream_select = QListWidget()
        self.refresh_btn = QPushButton("Refresh Streams")
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)

        self.refresh_btn.clicked.connect(self.refresh_streams)
        self.connect_btn.clicked.connect(self.connect_streams)
        self.disconnect_btn.clicked.connect(self.disconnect_streams)

        # --- Logging
        self.toggle_btn = QPushButton("Start Logging")
        self.toggle_btn.setEnabled(False)
        self.toggle_btn.clicked.connect(self.toggle_logging)

        # --- Status and Folder
        self.status = QLabel("Idle")
        self.status.setAlignment(Qt.AlignCenter)
        self.log_dir = r'logs/streams'
        self.dir_btn = QPushButton("Select Log Folder")
        self.dir_btn.clicked.connect(self.select_folder)

        # --- Layout Setup
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel("Available LSL Streams:"))
        self.layout.addWidget(self.stream_select)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.disconnect_btn)
        self.layout.addLayout(btn_row)

        self.layout.addWidget(self.dir_btn)
        self.layout.addWidget(self.toggle_btn)
        self.layout.addWidget(self.status)

        # --- Plot Container
        self.plot_container = QVBoxLayout()
        self.scroll_area = QScrollArea()
        self.scroll_content = QWidget()
        self.scroll_content.setLayout(self.plot_container)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)

        self.plus_button = self._make_plus_button()
        self.plot_container.addWidget(self.plus_button)
        self.plus_button.setEnabled(False)

        self.layout.addWidget(QLabel("Interactive Plots"))
        self.layout.addWidget(self.scroll_area)

        # --- Poll Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_all)

        # --- Initial Stream Load
        self.refresh_streams()

    # ---------------------- UI Actions ----------------------

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

    def _make_plus_button(self):
        btn = QPushButton("+")
        btn.setFixedSize(40, 40)
        btn.clicked.connect(self.add_plot_dialog)
        return btn

    # ---------------------- Connection & Logging ----------------------

    def connect_streams(self):
        self.connected_loggers = []
        for i in range(self.stream_select.count()):
            item = self.stream_select.item(i)
            if item.checkState() == Qt.Checked:
                stream = self.available[i]
                inlet = StreamInlet(stream)
                logger = BinaryStreamLogger(inlet, os.devnull)  # placeholder path
                self.connected_loggers.append(logger)

        if not self.connected_loggers:
            self.status.setText("No streams selected.")
            return

        self.status.setText(f"Connected to {len(self.connected_loggers)} stream(s)")
        self.toggle_btn.setEnabled(True)
        self.plus_button.setEnabled(True)
        self.stream_select.setDisabled(True)
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)

    def disconnect_streams(self):
        if self.active_loggers:
            self.status.setText("Stop logging before disconnecting.")
            return

        for logger in self.connected_loggers:
            logger.close()
        self.connected_loggers = []

        self.status.setText("Disconnected.")
        self.toggle_btn.setEnabled(False)
        self.plus_button.setEnabled(False)
        self.stream_select.setDisabled(False)
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

    def toggle_logging(self):
        if not self.connected_loggers:
            self.status.setText("Must connect to streams before logging.")
            return

        if self.active_loggers:
            self.timer.stop()
            for logger in self.active_loggers:
                logger.close()
            self.active_loggers = []
            self.toggle_btn.setText("Start Logging")
            self.status.setText("Logging stopped.")
            self.disconnect_btn.setEnabled(True)
        else:
            os.makedirs(self.log_dir, exist_ok=True)
            self.active_loggers = []
            for logger in self.connected_loggers:
                stream = logger.inlet.info()
                fname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{stream.name()}.bin"
                path = os.path.join(self.log_dir, fname)
                new_logger = BinaryStreamLogger(logger.inlet, path)
                self.active_loggers.append(new_logger)
            self.timer.start(50)
            self.toggle_btn.setText("Stop Logging")
            self.status.setText(f"Logging {len(self.active_loggers)} stream(s)...")
            self.disconnect_btn.setEnabled(False)

    def poll_all(self):
        for logger in self.active_loggers:
            logger.log_chunk()

    # ---------------------- Plot Management ----------------------

    def add_plot_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Plot")
        layout = QVBoxLayout(dialog)

        # Plot type selection
        plot_type_box = QComboBox()
        plot_type_box.addItems(["TimeSeries", "TimeSeries Array"])

        # Logger selection
        logger_box = QComboBox()
        for logger in self.connected_loggers:
            logger_box.addItem(logger.inlet.info().name(), userData=logger)

        layout.addWidget(QLabel("Select Plot Type:"))
        layout.addWidget(plot_type_box)
        layout.addWidget(QLabel("Select Stream:"))
        layout.addWidget(logger_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            plot_type = plot_type_box.currentText()
            logger = logger_box.currentData()

            if plot_type == "TimeSeries" and logger:
                self.create_plot(TimeSeriesPlot, logger)
            elif plot_type == "TimeSeries Array" and logger:
                self.create_plot(TimeSeriesArray, logger)

    def create_plot(self, plot_class, logger):
        self.plot_container.removeWidget(self.plus_button)
        self.plus_button.setParent(None)

        plot = plot_class(parent=self.scroll_content, logger=logger, on_close=self.remove_plot)
        self.plot_widgets.append(plot)

        base_width = getattr(plot, "minimum_display_width", 800)
        base_height = getattr(plot, "preferred_height", 300)
        margin = 100

        # Total required height
        estimated_height = base_height * len(self.plot_widgets) + margin

        # Get screen size
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        screen_w = screen.width()
        screen_h = screen.height()

        if estimated_height < screen_h:
            # Add to primary plot container
            self.plot_container.addWidget(plot)
            self.plot_container.addWidget(self.plus_button)
            self.scroll_area.setVisible(True)
            self.resize(max(self.width(), base_width + margin), estimated_height)
            if hasattr(self, 'secondary_container'):
                self.secondary_container.setVisible(False)
        else:
            # Use secondary column
            if not hasattr(self, 'secondary_container'):
                self.secondary_container = QVBoxLayout()
                self.secondary_panel = QWidget()
                self.secondary_panel.setLayout(self.secondary_container)
                self.secondary_area = QScrollArea()
                self.secondary_area.setWidget(self.secondary_panel)
                self.secondary_area.setWidgetResizable(True)
                self.scroll_splitter.addWidget(self.secondary_area)
                self.scroll_splitter.setSizes([1, 1])

            self.secondary_container.addWidget(plot)
            self.secondary_container.addWidget(self.plus_button)
            self.secondary_area.setVisible(True)
            self.resize(min(self.width() * 2, screen_w), screen_h - 100)

        # Keep window resizable if plots are removed later
        self.scroll_content.adjustSize()

    def remove_plot(self, plot_widget):
        if plot_widget in self.plot_widgets:
            self.plot_widgets.remove(plot_widget)
            plot_widget.cleanup()
            plot_widget.setParent(None)
            plot_widget.deleteLater()
