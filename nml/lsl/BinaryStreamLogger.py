import struct
import os
import json
import numpy as np
from pylsl import StreamInlet


class BinaryStreamLogger:
    HEADER_MAGIC = b'LSLB'
    VERSION = 1

    def __init__(self, inlet: StreamInlet, output_path: str):
        self.inlet = inlet
        self.outfile = open(output_path, 'wb')
        self.write_header()

    def write_header(self):
        info = self.inlet.info()
        name = info.name()
        name_bytes = name.encode('utf-8')
        n_channels = info.channel_count()
        srate = info.nominal_srate()
        fmt_enum = info.channel_format()

        # Format mapping
        format_map = {
            1: (0, np.float32),  # float32
            2: (1, np.float64),  # double64
        }
        fmt_code, self.sample_dtype = format_map.get(fmt_enum, (255, None))
        if self.sample_dtype is None:
            raise ValueError(f"Unsupported channel format: {fmt_enum}")

        # === Channel Metadata ===
        ch_names = []
        ch_units = []

        chs = info.desc().child("channels").child("channel")
        for _ in range(n_channels):
            ch_names.append(chs.child_value("label") or f"ch{_}")
            ch_units.append(chs.child_value("unit") or "unknown")
            chs = chs.next_sibling()

        # Get first sample to log its timestamp
        chunk, timestamps = self.inlet.pull_chunk(timeout=1.0)
        if not timestamps:
            raise RuntimeError("Could not read first timestamp from stream")
        start_time = timestamps[0]
        self.pending_chunk = (chunk, timestamps)

        metadata = {
            "version": 2,
            "channel_names": ch_names,
            "units": ch_units,
            "source_id": info.source_id(),
            "start_time": start_time
        }

        metadata_json = json.dumps(metadata).encode('utf-8')
        meta_len = len(metadata_json)

        # === Header Write ===
        header = struct.pack(
            '<4sIIfII',                # Magic, Version, nCh, srate, fmt_code, name_len
            self.HEADER_MAGIC,
            self.VERSION,
            n_channels,
            srate,
            fmt_code,
            len(name_bytes)
        )
        self.outfile.write(header)
        self.outfile.write(name_bytes)

        # Write metadata block
        self.outfile.write(struct.pack('<I', meta_len))
        self.outfile.write(metadata_json)


    def log_chunk(self):
        if hasattr(self, 'pending_chunk'):
            chunk, timestamps = self.pending_chunk
            del self.pending_chunk
        else:
            chunk, timestamps = self.inlet.pull_chunk(timeout=0.1)

        if not timestamps:
            return

        arr = np.array(chunk, dtype=self.sample_dtype)  # shape: (samples, channels)
        arr = arr.T  # shape: (channels, samples)

        for ts, col in zip(timestamps, arr.T):
            self.outfile.write(struct.pack('<d', ts))
            self.outfile.write(col.tobytes())

    def close(self):
        self.outfile.close()
