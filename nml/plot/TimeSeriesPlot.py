from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QComboBox
import pyqtgraph as pg
import numpy as np
from .BasePlot import BasePlot


class TimeSeriesPlot(BasePlot):
    minimum_display_width = 900  # class attribute
    y_min: int = -250
    y_max: int = 250

    def _build_controls(self):
        self.channel_select = QComboBox()
        ch_names = self.logger.inlet.info().desc().child("channels").child("channel")

        self.channel_labels = []
        for _ in range(self.logger.inlet.info().channel_count()):
            label = ch_names.child_value("label") or f"Channel {_}"
            self.channel_labels.append(label)
            self.channel_select.addItem(label)
            ch_names = ch_names.next_sibling()

        self.channel_select.currentIndexChanged.connect(self.update_plot_channel)
        self.current_channel = 0
        return self.channel_select

    def _build_plot(self):
        plot_widget = pg.PlotWidget()
        plot_widget.setYRange(-250, 250)  # default range
        self.curve = plot_widget.plot(pen='y')
        self.data = []
        return plot_widget


    def update_plot_channel(self, index):
        self.current_channel = index
        self.data = []  # reset buffer
        label = self.channel_labels[index]

        if label.upper() == "TRIGGERS":
            self.plot_widget.setYRange(-0.1, 1.1)
            self.plot_widget.getAxis('left').setTicks([
                [(0, "LOW"), (1, "HIGH")]
            ])
            self.plot_widget.enableAutoRange('y', False)

        elif label.upper() in ("STATUS", "COUNTER"):
            self.plot_widget.enableAutoRange('y', True)
            self.plot_widget.getAxis('left').setTicks([])  # default

        else:
            self.plot_widget.setYRange(-250, 250)
            self.plot_widget.getAxis('left').setTicks([])
            self.plot_widget.enableAutoRange('y', False)


    def timerEvent(self, event):
        chunk, timestamps = self.logger.inlet.pull_chunk(timeout=0.0)
        if timestamps:
            new_data = [sample[self.current_channel] for sample in chunk]
            self.data.extend(new_data)
            self.data = self.data[-1000:]
            self.curve.setData(self.data)
