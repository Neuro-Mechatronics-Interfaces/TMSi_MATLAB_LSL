import os
import yaml
from pathlib import Path

class TimeSeriesArrayConfig:
    def __init__(self, config_path=None):
        self.config_path = Path(config_path or "config/TimeSeriesArray.config")
        self.configs = []
        self.load()

    def load(self):
        if not self.config_path.exists():
            print(f"[INFO] Config file not found: {self.config_path}")
            self.configs = []
            return
        with open(self.config_path, 'r') as f:
            self.configs = yaml.safe_load(f) or []

    def save(self):
        os.makedirs(self.config_path.parent, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.configs, f, sort_keys=False)

    def list_array_names(self):
        return [entry['Name'] for entry in self.configs]

    def get_array(self, name):
        for entry in self.configs:
            if entry['Name'] == name:
                return entry
        return None

    def get_grid(self, array_name, grid_name):
        array = self.get_array(array_name)
        if array:
            for grid in array.get('Grids', []):
                if grid['Name'] == grid_name:
                    return grid
        return None

    def add_or_update_array(self, array_name, grids):
        for entry in self.configs:
            if entry['Name'] == array_name:
                entry['Grids'] = grids
                return
        self.configs.append({'Name': array_name, 'Grids': grids})

    def remove_array(self, array_name):
        self.configs = [cfg for cfg in self.configs if cfg['Name'] != array_name]
