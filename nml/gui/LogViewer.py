import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QFileDialog, QPushButton, QSplitter, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
import pyqtgraph as pg
import pandas as pd
from nml.lsl.StreamLogReader import StreamLogReader

class LogViewer(QWidget):
    def __init__(self, root_folder=r'logs\streams'):
        super().__init__()
        self.setWindowTitle("Stream Log Viewer")
        self.resize(1000, 600)
        self.marker_items = []   # To store pg.InfiniteLine + TextItem
        self.signal_curve = None  # To track the main signal plot

        self.metadata_folder = r'logs\metadata'
        self.metadata_list = QListWidget()
        self.metadata_list.itemClicked.connect(self.load_metadata_session)
        self.select_metadata_btn = QPushButton("Select Metadata Folder")
        self.select_metadata_btn.clicked.connect(self.select_metadata_folder)
        self.select_stream_btn = QPushButton("Select Stream Folder")
        self.select_stream_btn.clicked.connect(self.select_stream_folder)
        self.root_folder = root_folder
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Recording Logs"])
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemExpanded.connect(self.on_item_expanded)

        self.plot_widget = pg.PlotWidget(title="Channel Plot")
        self.plot_widget.showGrid(x=True, y=True)

        self.refresh_btn = QPushButton("Refresh Log List")
        self.refresh_btn.clicked.connect(self.refresh_log_tree)

        left_layout = QVBoxLayout()
        left_layout.insertWidget(0, self.select_stream_btn)                    
        left_layout.insertWidget(1, self.select_metadata_btn)
        left_layout.insertWidget(2, QLabel("Metadata Sessions"))
        left_layout.insertWidget(3, self.metadata_list)
        left_layout.insertWidget(4, QLabel("Available Recordings"))
        left_layout.insertWidget(5, self.tree)
        left_layout.insertWidget(6, self.refresh_btn)

        left_panel = QWidget()
        left_panel.setLayout(left_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.plot_widget)
        splitter.setSizes([300, 700])

        main_layout = QHBoxLayout()
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self.current_expanded = None
        self.refresh_log_tree()
        self.load_metadata_sessions()

    def select_stream_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Stream Folder", self.root_folder)
        if folder:
            self.root_folder = folder
            self.refresh_log_tree()

    def select_metadata_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Metadata Folder", self.metadata_folder)
        if folder:
            self.metadata_folder = folder
            self.load_metadata_sessions()

    def load_metadata_session(self, item):
        prefix = item.data(Qt.UserRole)
        trials_path = os.path.join(self.metadata_folder, f"logger_{prefix}_trials.csv")
        if not os.path.exists(trials_path):
            return

        try:
            df = pd.read_csv(trials_path)
        except Exception as e:
            print(f"Failed to read trials CSV: {e}")
            return

        # Remove previous markers
        for marker in self.marker_items:
            self.plot_widget.removeItem(marker)
        self.marker_items = []
        self.current_markers = []

        for _, row in df.iterrows():
            ts = row['Timestamp']
            label_text = row['Event']
            line = pg.InfiniteLine(pos=ts, angle=90, pen=pg.mkPen('r', width=1))
            label = pg.TextItem(text=label_text, color='r')
            label.setPos(ts, 0)

            self.plot_widget.addItem(line)
            self.plot_widget.addItem(label)

            self.marker_items.extend([line, label])
            self.current_markers.append({'line': line, 'label': label})


    def load_metadata_sessions(self):
        self.metadata_list.clear()
        if not os.path.exists(self.metadata_folder):
            return

        seen_sessions = set()
        for filename in os.listdir(self.metadata_folder):
            if not filename.startswith("logger_") or not filename.endswith(".csv"):
                continue
            try:
                # Parse: logger_YYYYMMDD_HHMMSS_SUFFIX_type.csv
                parts = filename.replace(".csv", "").split("_")
                timestamp = parts[1] + "_" + parts[2]
                suffix = "_".join(parts[3:-1])  # everything up to last part
                session_key = f"{timestamp}_{suffix}"
            except Exception:
                continue

            if session_key in seen_sessions:
                continue
            seen_sessions.add(session_key)

            # Human-readable timestamp
            try:
                dt_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"
            except Exception:
                dt_str = timestamp

            label = f"{dt_str} — {suffix}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, session_key)
            self.metadata_list.addItem(item)

    def on_item_expanded(self, item):
        parent = item.parent()
        if parent is None:
            self.populate_channels(item)


    def on_item_clicked(self, item, column):
        parent = item.parent()
        if parent is None:
            # Top-level item = recording → populate channels
            if not item.isExpanded():
                item.setExpanded(True)
            self.populate_channels(item)
        else:
            # Child item = channel → plot it
            self.plot_channel(item, column)


    def refresh_log_tree(self):
        self.tree.clear()
        if not os.path.exists(self.root_folder):
            return
        for file in os.listdir(self.root_folder):
            if file.endswith(".bin"):
                item = QTreeWidgetItem([file])
                item.setData(0, Qt.UserRole, os.path.join(self.root_folder, file))
                item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
                self.tree.addTopLevelItem(item)

    def populate_channels(self, item):
        print("Populating channels for:", item.text(0))
        if self.current_expanded and self.current_expanded != item:
            self.current_expanded.setExpanded(False)
            self.current_expanded.takeChildren()
        self.current_expanded = item

        filepath = item.data(0, Qt.UserRole)
        reader = StreamLogReader(filepath)
        try:
            result = reader.load()
        except Exception as e:
            print(f"Failed to load: {e}")
            return

        timestamps = result["timestamps"]
        data = result["data"]
        metadata = result.get("metadata", {})
        self.stream_start_time = metadata.get("start_time", timestamps[0])  # store absolute offset

        ch_names = metadata.get("channel_names", [f"Channel {i}" for i in range(data.shape[1])])
        item.takeChildren()

        for ch_index, ch_label in enumerate(ch_names):
            ch_item = QTreeWidgetItem([ch_label])
            ch_item.setData(0, Qt.UserRole, (timestamps, data[:, ch_index]))
            item.addChild(ch_item)

    def plot_channel(self, item, column):
        data = item.data(0, Qt.UserRole)
        if isinstance(data, tuple):
            t, y = data
            self.plot_widget.clear()
            self.marker_items = []

            # Plot using true LSL time
            self.signal_curve = self.plot_widget.plot(t, y, pen='y')

            for marker in getattr(self, "current_markers", []):
                self.plot_widget.addItem(marker['line'])
                self.plot_widget.addItem(marker['label'])
                self.marker_items.append(marker['line'])
                self.marker_items.append(marker['label'])
            self.plot_widget.setXRange(t[0], t[-1], padding=0.02)

