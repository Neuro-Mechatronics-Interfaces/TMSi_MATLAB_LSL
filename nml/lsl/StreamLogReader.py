import struct
import json
import numpy as np


class StreamLogReader:
    def __init__(self, path):
        self.path = path

    def load(self):
        with open(self.path, 'rb') as f:
            magic = f.read(4)
            if magic != b'LSLB':
                raise ValueError("Invalid log format.")

            version, nch, srate, fmt_code, name_len = struct.unpack('<IIfII', f.read(20))
            name = f.read(name_len).decode('utf-8')

            meta_len_bytes = f.read(4)
            if not meta_len_bytes:
                raise ValueError("Missing metadata length field after stream name.")
            meta_len = struct.unpack('<I', meta_len_bytes)[0]
            metadata_json = f.read(meta_len).decode('utf-8')
            metadata = json.loads(metadata_json)

            # Determine dtype
            if fmt_code == 0:
                dtype = np.float32
            elif fmt_code == 1:
                dtype = np.float64
            else:
                raise ValueError(f"Unsupported format code: {fmt_code}")

            # Read data body
            timestamps = []
            samples = []
            sample_size = nch * dtype().nbytes

            while True:
                ts_bytes = f.read(8)
                if not ts_bytes:
                    break
                if len(ts_bytes) < 8:
                    raise EOFError("Unexpected end of file while reading timestamp.")
                ts = struct.unpack('<d', ts_bytes)[0]

                sample_data = f.read(sample_size)
                if len(sample_data) < sample_size:
                    raise EOFError("Unexpected end of file while reading sample data.")

                data = np.frombuffer(sample_data, dtype=dtype)
                timestamps.append(ts)
                samples.append(data)

        # Provide fallback for legacy files
        metadata_version = metadata.get("version", 1)
        if metadata_version == 1 and "start_time" not in metadata:
            metadata["start_time"] = timestamps[0]  # Estimate

        return {
            "stream_name": name,
            "sampling_rate": srate,
            "timestamps": np.array(timestamps),
            "data": np.stack(samples),
            "metadata": metadata
        }
