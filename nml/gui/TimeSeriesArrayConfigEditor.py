from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLineEdit, QFormLayout, QLabel, QSpinBox, QDialog, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt
from nml.config.TimeSeriesArrayConfig import TimeSeriesArrayConfig


class TimeSeriesArrayConfigEditor(QWidget):
    def __init__(self, config_handler=None):
        super().__init__()
        self.setWindowTitle("Time Series Array Config Editor")
        self.resize(600, 400)
        self.config_handler = config_handler or TimeSeriesArrayConfig()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.array_list = QListWidget()
        self.array_list.itemClicked.connect(self.on_array_selected)
        self.layout.addWidget(QLabel("Array Configurations"))
        self.layout.addWidget(self.array_list)

        # Button row
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add New")
        self.del_btn = QPushButton("Delete Selected")
        self.save_btn = QPushButton("Save Changes")
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addWidget(self.save_btn)
        self.layout.addLayout(btn_row)

        self.add_btn.clicked.connect(self.add_array)
        self.del_btn.clicked.connect(self.delete_selected)
        self.save_btn.clicked.connect(self.save)

        self.refresh_list()

    def refresh_list(self):
        self.array_list.clear()
        for name in self.config_handler.list_array_names():
            self.array_list.addItem(name)

    def on_array_selected(self, item):
        name = item.text()
        array = self.config_handler.get_array(name)
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit: {name}")
        layout = QVBoxLayout(dialog)

        form_layouts = []
        grid_widgets = []

        for grid in array.get("Grids", []):
            form = QFormLayout()
            name_edit = QLineEdit(grid["Name"])
            rows = QSpinBox(); rows.setValue(grid["Rows"])
            cols = QSpinBox(); cols.setValue(grid["Columns"])
            chs = QSpinBox();  chs.setValue(grid["Channels"])
            form.addRow("Grid Name", name_edit)
            form.addRow("Rows", rows)
            form.addRow("Cols", cols)
            form.addRow("Channels", chs)
            layout.addLayout(form)
            grid_widgets.append((name_edit, rows, cols, chs))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        def apply_changes():
            new_grids = []
            for w in grid_widgets:
                new_grids.append({
                    "Name": w[0].text(),
                    "Rows": w[1].value(),
                    "Columns": w[2].value(),
                    "Channels": w[3].value()
                })
            self.config_handler.add_or_update_array(name, new_grids)
            dialog.accept()

        buttons.accepted.connect(apply_changes)
        buttons.rejected.connect(dialog.reject)
        dialog.exec_()

    def add_array(self):
        name, ok = QLineEdit.getText(self, "New Array", "Enter new array name:")
        if not ok or not name.strip():
            return
        self.config_handler.add_or_update_array(name.strip(), [])
        self.refresh_list()

    def delete_selected(self):
        item = self.array_list.currentItem()
        if item:
            self.config_handler.remove_array(item.text())
            self.refresh_list()

    def save(self):
        self.config_handler.save()
        QMessageBox.information(self, "Saved", "Configuration saved successfully.")
