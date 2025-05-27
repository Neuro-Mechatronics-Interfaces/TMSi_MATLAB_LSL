from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSpinBox, QFrame
)
import pyqtgraph as pg
import numpy as np
import matplotlib.pyplot as plt 
from nml.config.TimeSeriesArrayConfig import TimeSeriesArrayConfig
from nml.gui.TimeSeriesArrayConfigEditor import TimeSeriesArrayConfigEditor
from nml.plot.BasePlot import BasePlot

class TimeSeriesArray(BasePlot):
    minimum_display_width = 900  # class attribute
    preferred_height: int = 600 
    n_channels: int = 64
    duration_ms: int = 1000 # horizontal scale
    v_spacing: int = 50 # vertical spacing between traces

    def __init__(self, logger, parent=None, on_close=None):
        super().__init__(parent=parent, logger=logger, on_close=on_close, cfg_handler=TimeSeriesArrayConfig(), buffer=np.zeros((self.n_channels, 2000)))  

    def rebuild_plot(self):
        if self.plot_widget:
            self._build_plot()  # reuses the same widget

    def _build_controls(self):
        container = QWidget()
        control_row = QHBoxLayout(container)
        container.setLayout(control_row)

        control_row.addWidget(QLabel("Grid Config:"))
        self.grid_select = QComboBox()
        self.grid_select.addItems(self.cfg_handler.list_array_names())
        control_row.addWidget(self.grid_select)
        self.grid_select.currentIndexChanged.connect(self.rebuild_plot)

        self.edit_btn = QPushButton("Edit Configs")
        control_row.addWidget(self.edit_btn)
        self.edit_btn.clicked.connect(self.launch_editor)

        control_row.addWidget(QLabel("Duration (ms):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(100, 5000)
        self.duration_spin.setValue(self.duration_ms)
        control_row.addWidget(self.duration_spin)
        self.duration_spin.valueChanged.connect(self.rebuild_plot)

        control_row.addWidget(QLabel("Spacing:"))
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(10, 500)
        self.spacing_spin.setValue(self.v_spacing)
        control_row.addWidget(self.spacing_spin)
        self.spacing_spin.valueChanged.connect(self.rebuild_plot)

        return container

    def _build_plot(self, *args):
        # Plot area
        if self.plot_widget is None:
            plot_widget = pg.PlotWidget()
            plot_widget.enableAutoRange(y=True)
            plot_widget.enableAutoRange(x=True)
        else:  
            plot_widget = self.plot_widget
            plot_widget.clear()
        self.curves = []
        self.grid_labels = []
        array_name = self.grid_select.currentText()
        array_cfg = self.cfg_handler.get_array(array_name)
        if not array_cfg:
            return

        offset_x = 1.05 * self.duration_ms / 1000.0
        offset_y = self.v_spacing
        total_len = self.buffer.shape[1]
        t = np.linspace(-offset_x, 0, total_len)

        prev_grid_ch = 0
        grid_ch = array_cfg["Grids"][0]["Channels"]
        i_grid = 0
        cmap = plt.get_cmap(array_cfg["Grids"][0]["Colormap"])
        top_row_y_offsets = []
        col_x_centers = []

        for idx in range(self.n_channels):
            if idx == grid_ch:
                if top_row_y_offsets and col_x_centers:
                    grid_name = array_cfg["Grids"][i_grid]["Name"]
                    self._add_grid_label(plot_widget, grid_name, col_x_centers, top_row_y_offsets, offset_y)
                    col_x_centers = []
                    top_row_y_offsets = []
                i_grid = i_grid + 1
                prev_grid_ch = grid_ch
                grid_ch = grid_ch + array_cfg["Grids"][i_grid]["Channels"]
                cmap = plt.get_cmap(array_cfg["Grids"][i_grid]["Colormap"])
            col = (idx - prev_grid_ch) // array_cfg["Grids"][i_grid]["Rows"]
            row = idx % array_cfg["Grids"][i_grid]["Rows"]
            x_offset = col * offset_x + array_cfg["Grids"][i_grid]["X_Offset"]
            y_offset = -row * offset_y + array_cfg["Grids"][i_grid]["Y_Offset"]
            color = cmap((idx + 10 - prev_grid_ch) / max(self.n_channels + 10 - 1, 1))  # Normalized 0–1
            color_255 = tuple(int(c * 255) for c in color[:3]) 
            pen = pg.mkPen(color=color_255, width=0.7)
            curve = plot_widget.plot(t + x_offset, self.buffer[idx] + y_offset, pen=pen)
            self.curves.append((curve, y_offset, x_offset))
            if row == 0:
                top_row_y_offsets.append(y_offset)
            col_x_centers.append(x_offset)

        # Add label for final grid
        if top_row_y_offsets and col_x_centers:
            grid_name = array_cfg["Grids"][i_grid]["Name"]
            self._add_grid_label(plot_widget, grid_name, col_x_centers, top_row_y_offsets, offset_y)
        return plot_widget

    def _add_grid_label(self, plot_widget: pg.PlotWidget, name: str, x_centers, y_offsets, row_spacing):
        if not x_centers or not y_offsets:
            return
        x_label = np.mean(x_centers)
        y_label = min(y_offsets) + row_spacing  # Offset 1 row above
        label = pg.TextItem(name, color='w', anchor=(0.5, 0))
        label.setPos(x_label, y_label)
        plot_widget.addItem(label)
        self.grid_labels.append(label)

    def launch_editor(self):
        editor = TimeSeriesArrayConfigEditor(self.cfg_handler)
        editor.show()

    def timerEvent(self, event):
        chunk, timestamps = self.inlet.pull_chunk(timeout=0.0)
        if not timestamps:
            return

        new_data = np.array(chunk).T  # [channels x samples]
        n = new_data.shape[1]
        self.buffer = np.roll(self.buffer, -n, axis=1)
        self.buffer[:, -n:] = new_data[:64, :]
        self.update_plot()

    def update_plot(self):
        total_len = self.buffer.shape[1]
        offset_x = self.duration_spin.value() / 1000.0
        t = np.linspace(0, offset_x, total_len)
        for idx, (curve, y_off, x_off) in enumerate(self.curves):
            y = self.buffer[idx] + y_off
            curve.setData(t + x_off, y)
