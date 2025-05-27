from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
import pyqtgraph as pg

class BasePlot(QWidget):
    preferred_height: int = 300
    plot_widget: pg.PlotWidget = None

    def __init__(self, parent=None, logger=None, on_close=None, cfg_handler=None, buffer=None):
        super().__init__(parent)
        self.logger = logger
        self.inlet = logger.inlet
        self.cfg_handler = cfg_handler
        self.on_close = on_close
        self.buffer = buffer

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        plot_height = getattr(self, "preferred_height", 300)
        self.setMinimumHeight(plot_height)
        self.setMaximumHeight(plot_height)

        # Header with close button
        header_layout = QHBoxLayout()
        close_btn = QPushButton("✖")
        close_btn.setFixedWidth(20)
        close_btn.clicked.connect(self.close_plot)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        self.layout.addLayout(header_layout)
        self.controls_widget = self._build_controls()
        self.plot_widget = self._build_plot()
        self.layout.addWidget(self.controls_widget)
        self.layout.addWidget(self.plot_widget)
        self.timer = self.startTimer(100)

    def _build_controls(self):
        return QWidget()  # Override in subclass

    def _build_plot(self):
        return QWidget()  # Override in subclass

    def close_plot(self):
        if callable(self.on_close):
            self.on_close(self)
        self.cleanup()
        self.setParent(None)
        self.deleteLater()

    def cleanup(self):
        self.killTimer(self.timer)

    def timerEvent(self, event):
        pass # Main handling of inlet/data buffer to update plot data values goes here