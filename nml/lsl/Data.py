import os
import glob
import json
import struct
import numpy as np
import pandas as pd
from nml.lsl.StreamLogReader import StreamLogReader


class Data:
    def __init__(self,
                 stream_key: str,                 # e.g. '20250526_161028'
                 metadata_key_or_suffix: str,     # e.g. '20250526_161028' or 'DEFAULT'
                 stream_folder: str = r'logs\streams',
                 metadata_folder: str = r'logs\metadata'):

        self.stream_key = stream_key
        self.stream_folder = stream_folder
        self.metadata_folder = metadata_folder

        # Determine if metadata_key_or_suffix is a full timestamp or a suffix
        if self._is_timestamp_format(metadata_key_or_suffix):
            self.metadata_key = metadata_key_or_suffix
            self.metadata_suffix = "DEFAULT"
        else:
            self.metadata_suffix = metadata_key_or_suffix
            self.metadata_key = self._find_first_metadata_key_for_suffix(self.metadata_suffix)

        self.signal = None           # np.ndarray [n_ch, n_samples]
        self.timestamps = None       # np.ndarray [n_samples]
        self.metadata = {}           # dict of DataFrames

        self._load_stream()
        self._load_metadata()

    def _find_first_metadata_key_for_suffix(self, suffix):
        pattern = os.path.join(self.metadata_folder, f"logger_*_{suffix}_*.csv")
        files = glob.glob(pattern)
        keys = []
        for f in files:
            try:
                basename = os.path.basename(f)
                parts = basename.split("_")
                if len(parts) >= 4:
                    key = f"{parts[1]}_{parts[2]}"
                    keys.append(key)
            except Exception:
                continue
        if not keys:
            raise FileNotFoundError(f"No metadata files found with suffix '{suffix}' in {self.metadata_folder}")
        return sorted(keys)[0]  # lexically first = earliest in YYYYMMDD_HHMMSS


    def _is_timestamp_format(self, s):
        return len(s) == 15 and s[:8].isdigit() and s[9:].isdigit() and s[8] == "_"

    def _find_stream_file(self):
        pattern = os.path.join(self.stream_folder, f"{self.stream_key}*.bin")
        matches = glob.glob(pattern)
        if not matches:
            raise FileNotFoundError(f"No stream log found for key: {self.stream_key}")
        return matches[0]

    def _load_stream(self):
        path = self._find_stream_file()
        reader = StreamLogReader(path)
        result = reader.load()

        self.signal = result['data'].T
        self.timestamps = result['timestamps']
        self.metadata['stream'] = result['metadata']

    def _load_metadata(self):
        suffixes = ['state', 'parameter', 'filename', 'trials']
        for suffix in suffixes:
            fname = f"logger_{self.metadata_key}_{self.metadata_suffix}_{suffix}.csv"
            path = os.path.join(self.metadata_folder, fname)
            if os.path.exists(path):
                try:
                    self.metadata[suffix] = pd.read_csv(path)
                except Exception as e:
                    print(f"Failed to read metadata file {suffix}: {e}")

    def get_stream_data(self):
        return self.signal, self.timestamps

    def get_events(self, event_type='trials'):
        return self.metadata.get(event_type, pd.DataFrame())
