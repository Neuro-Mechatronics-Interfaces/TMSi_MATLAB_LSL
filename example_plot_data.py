import matplotlib.pyplot as plt
import numpy as np
from nml.lsl.Data import Data

# d = Data('20250526_163645', 'DEFAULT') # Will grab first file in logs/metadata with "DEFAULT" suffix
d = Data('20250526_163645', '20250526_163724') # Equivalent, if you only have one session with "DEFAULT"
sig, ts = d.get_stream_data()
ch_names = d.metadata['stream']['channel_names']
print(ch_names) # Saved in header metadata of binaries

trials = d.get_events('trials')
print(trials)

plt.figure(figsize=(12, 4))
plt.plot(ts, sig[-1], label="COUNTER Channel")

# Add trial event markers
for _, row in trials.iterrows():
    plt.axvline(row['Timestamp'], color='red', linestyle='--')
    plt.text(row['Timestamp'], plt.ylim()[1]*0.9, row['Event'], rotation=90)

plt.xlabel("Time (s)")
plt.ylabel("Amplitude")
plt.title("COUNTER with Trial Markers")
plt.legend()
plt.tight_layout()
plt.show()

uni_indices = [i for i, name in enumerate(ch_names) if "UNI" in name]
signal_uni = d.signal[uni_indices, :]  # shape: [UNI_channels, samples]

starts = d.get_events('trials')[lambda df: df['Event'] == 'Recording Start']['Timestamp'].values
ends = d.get_events('trials')[lambda df: df['Event'] == 'Recording End']['Timestamp'].values

segments = []

for start, end in zip(starts, ends):
    mask = (d.timestamps >= start) & (d.timestamps <= end)
    trial = signal_uni[:, mask]
    segments.append(trial)

print("Segments for each trial:")
print(segments) # segments now contains the signal segments for monopolar textile arrays, for each trial

# RMS per trial across UNI channels
print("RMS per trial across UNI channels:")
rms_uni_by_trial = [np.sqrt(np.mean(trial**2, axis=1)) for trial in segments]  # list of [n_UNI_channels] arrays
print(rms_uni_by_trial)