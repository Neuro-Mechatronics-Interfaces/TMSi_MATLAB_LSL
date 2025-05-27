import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QLabel, QSpinBox, QComboBox, QHBoxLayout, QWidget, QDoubleSpinBox
from nml.plot.BasePlot import BasePlot
from scipy.signal import butter, lfilter, lfilter_zi
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt 
from nml.plot.Filters import OneEuroFilter

class EnvelopeGridImage(BasePlot):
    preferred_height = 500
    interpolation_factor: int = 4
    fs: float = 2000  # Default sampling rate
    hp_cutoff: int = 100
    env_lp_cutoff: int = 10
    min_cutoff: float = 0.25
    beta: float = 0.05
    d_cutoff: float = 5.0
    grid_layout = None
    euro_filters = [
            OneEuroFilter(freq=2000, min_cutoff=0.25, beta=0.05, d_cutoff=5.0)
            for _ in range(64)
        ] 

    def __init__(self, logger, parent=None, on_close=None):
        super().__init__(parent=parent, logger=logger, on_close=on_close, buffer=np.zeros((64, 500)))     
        self.hp_b, self.hp_a = butter(1, self.hp_cutoff / (0.5 * self.fs), btype='high')
        self.env_lp_b, self.env_lp_a = butter(
            1, self.env_lp_cutoff / (0.5 * self.fs), btype='low'
        )
        # For HPF
        self.hp_zi = [lfilter_zi(self.hp_b, self.hp_a) * 0 for _ in range(64)]

        # For envelope LPF
        self.env_lp_zi = [lfilter_zi(self.env_lp_b, self.env_lp_a) * 0 for _ in range(64)]

    def _build_controls(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("HPF (Hz):"))
        self.hpf_box = QSpinBox()
        self.hpf_box.setRange(1, 1000)
        self.hpf_box.setValue(self.hp_cutoff)
        row.addWidget(self.hpf_box)

        row.addWidget(QLabel("Min Cutoff:"))
        self.min_cutoff_box = QDoubleSpinBox()
        self.min_cutoff_box.setRange(0.01, 10.0)
        self.min_cutoff_box.setDecimals(2)
        self.min_cutoff_box.setSingleStep(0.05)
        self.min_cutoff_box.setValue(0.25)
        row.addWidget(self.min_cutoff_box)
        self.min_cutoff_box.valueChanged.connect(self._update_euro_filters)

        row.addWidget(QLabel("Beta:"))
        self.beta_box = QDoubleSpinBox()
        self.beta_box.setRange(0.0, 1.0)
        self.beta_box.setDecimals(3)
        self.beta_box.setSingleStep(0.01)
        self.beta_box.setValue(0.05)
        row.addWidget(self.beta_box)
        self.beta_box.valueChanged.connect(self._update_euro_filters)

        row.addWidget(QLabel("D Cutoff:"))
        self.d_cutoff_box = QDoubleSpinBox()
        self.d_cutoff_box.setRange(0.01, 10.0)
        self.d_cutoff_box.setDecimals(2)
        self.d_cutoff_box.setSingleStep(0.1)
        self.d_cutoff_box.setValue(5.0)
        row.addWidget(self.d_cutoff_box)
        self.d_cutoff_box.valueChanged.connect(self._update_euro_filters)

        row.addWidget(QLabel("Interp. Factor:"))
        self.interp_box = QSpinBox()
        self.interp_box.setRange(1, 10)
        self.interp_box.setValue(self.interpolation_factor)
        row.addWidget(self.interp_box)
        self.interp_box.valueChanged.connect(self._update_interp_factor)

        row.addWidget(QLabel("Colormap:"))
        self.colormap_box = QComboBox()
        self.colormap_box.addItems(['plasma', 'viridis', 'YlOrRd', 'GnBu'])
        self.colormap_box.setCurrentText('plasma')
        row.addWidget(self.colormap_box)
        self.colormap_box.currentIndexChanged.connect(self._update_image)

        container = QWidget()
        container.setLayout(row)
        return container
    
    def _update_interp_factor(self):
        self.interpolation_factor = self.interp_box.value()


    def _update_euro_filters(self):
        min_cutoff = self.min_cutoff_box.value()
        beta = self.beta_box.value()
        d_cutoff = self.d_cutoff_box.value()

        self.euro_filters = [
            OneEuroFilter(freq=self.fs, min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)
            for _ in range(self.buffer.shape[0])
        ]

    def _build_plot(self):
        self.image_item = pg.ImageItem()
        plot = pg.PlotWidget()
        plot.addItem(self.image_item)
        plot.getViewBox().invertY(True)
        plot.enableAutoRange(y=True)
        plot.enableAutoRange(x=True)
        return plot

    def timerEvent(self, event):
        chunk, timestamps = self.inlet.pull_chunk(timeout=0.0)
        if not timestamps:
            return
        data = np.array(chunk).T  

        # Apply HPF with state
        hpf = np.zeros_like(data)
        for i in range(64):
            hpf[i], self.hp_zi[i] = lfilter(self.hp_b, self.hp_a, data[i], zi=self.hp_zi[i])

        # Rectify
        rectified = np.abs(hpf)

        # Apply 6 Hz LPF with state
        lp_filtered = np.zeros_like(rectified)
        for i in range(64):
            lp_filtered[i], self.env_lp_zi[i] = lfilter(self.env_lp_b, self.env_lp_a, rectified[i], zi=self.env_lp_zi[i])

        # Apply 1-Euro smoothing
        envelope = np.stack([
            np.array([f.filter(v) for v in channel])  # filtered signal per channel
            for f, channel in zip(self.euro_filters, lp_filtered)
        ])
        values = np.mean(envelope, axis=1)
        self._update_image(values)

    def _update_image(self, values=None):
        if values is not None:
            self.latest_values = values
        if not hasattr(self, "latest_values"):
            return
        values = self.latest_values
        interp = self.interp_box.value()
        cmap = plt.get_cmap(self.colormap_box.currentText())
        # Grid shape
        rows, cols = 8, 4
        gap_cols = 2
        total_cols = (cols * 2 + gap_cols) * interp
        canvas = np.full((rows * interp, total_cols), np.nan, dtype=np.float32)
        def interpolate_grid(grid_values, x_offset=0):
            coords = [(c + x_offset, r) for r in range(rows) for c in range(cols)]
            coords = np.array(coords)
            xs, ys = coords[:, 0], coords[:, 1]

            xi = np.linspace(0, cols - 1, cols * interp)
            yi = np.linspace(0, rows - 1, rows * interp)
            xi, yi = np.meshgrid(xi, yi, indexing='ij')
            zi = griddata(coords, grid_values, (xi + x_offset, yi), method='linear', fill_value=np.nan).T
            return zi
        # Grid A
        grid_a = values[:32]
        zi_a = interpolate_grid(grid_a, x_offset=0)
        canvas[:, :cols * interp] = zi_a
        # Grid B
        grid_b = values[32:]
        zi_b = interpolate_grid(grid_b, x_offset=cols + gap_cols)
        canvas[:, (cols + gap_cols) * interp:] = zi_b
        # Normalize and color
        if np.isnan(canvas).all():
            return
        zi_norm = (canvas - np.nanmin(canvas)) / (np.nanmax(canvas) - np.nanmin(canvas) + 1e-9)
        rgba = cmap(zi_norm)
        rgb = np.nan_to_num(rgba[:, :, :3], nan=0.0)
        rgb255 = (rgb * 255).astype(np.uint8).transpose(1, 0, 2)  # (width, height, 3)
        self.image_item.setImage(rgb255, levels=(0, 255))


    @staticmethod
    def generate_two_8x4_grid_coords(gap_x=2.0):
        coords = []
        # Grid A (left)
        for i in range(8):      # rows
            for j in range(4):  # cols
                coords.append((j, i))  # col, row

        # Grid B (right) — offset by gap_x and 4 columns
        for i in range(8):
            for j in range(4):
                coords.append((j + 4 + gap_x, i))
        return coords

    def _get_grid_coords(self):
        # For now assume 8x8 grid
        shape = (8, 8)
        coords = [(i, j) for i in range(8) for j in range(8)]
        return coords, shape
