"""
Audio Feature Extraction Frontend for CIMTinyTO Voice Keyword Spotting (KWS).
Extracts 16-channel Mel-filterbank spectrograms matching the 16x16 SCIM array.

Silicon Realities:
- 16 Mel channels maps 1:1 to the 16 activation inputs of the SCIM array.
- Frame length 480 samples (30 ms @ 16 kHz), hop 320 samples (20 ms).
- Hann window reduces spectral leakage at frame boundaries.
- Log-energy normalization projects speech dynamics into 8-bit uint8 [0, 255]
  driving the on-chip Linear Feedback Shift Register (LFSR) SNG bank.
"""

import numpy as np


def hz_to_mel(f_hz: float) -> float:
    """Convert frequency in Hertz to Mel scale."""
    return 2595.0 * np.log10(1.0 + f_hz / 700.0)


def mel_to_hz(mel: float) -> float:
    """Convert Mel scale value back to Hertz."""
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def create_mel_filterbank(
    num_channels: int = 16,
    n_fft: int = 512,
    sample_rate: int = 16000,
    f_min: float = 50.0,
    f_max: float = 4000.0,
) -> np.ndarray:
    """
    Construct triangular Mel filterbank matrix of shape (num_channels, n_fft // 2 + 1).

    Args:
        num_channels: Number of Mel frequency bands (default: 16 matching SCIM rows).
        n_fft: FFT size (default: 512).
        sample_rate: Sampling frequency in Hz (default: 16000).
        f_min: Lower acoustic cutoff frequency in Hz.
        f_max: Upper acoustic cutoff frequency in Hz (telephone bandwidth formant ceiling).

    Returns:
        np.ndarray of shape (num_channels, 257) with triangular weights.
    """
    num_bins = n_fft // 2 + 1
    mel_min = hz_to_mel(f_min)
    mel_max = hz_to_mel(f_max)

    # num_channels + 2 points to define left, center, right of each triangle
    mel_points = np.linspace(mel_min, mel_max, num_channels + 2)
    hz_points = mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
    bin_points = np.clip(bin_points, 0, num_bins - 1)

    filterbank = np.zeros((num_channels, num_bins), dtype=np.float32)
    for m in range(1, num_channels + 1):
        left = bin_points[m - 1]
        center = bin_points[m]
        right = bin_points[m + 1]

        # Rising slope
        if center > left:
            for k in range(left, center):
                filterbank[m - 1, k] = (k - left) / (center - left)
        # Falling slope
        if right > center:
            for k in range(center, right):
                filterbank[m - 1, k] = (right - k) / (right - center)

    # Normalize area of each triangle to prevent high-frequency energy inflation
    area = np.sum(filterbank, axis=1, keepdims=True)
    area = np.where(area > 0, area, 1.0)
    filterbank = filterbank / area

    return filterbank


def extract_mel_filterbank(
    waveform: np.ndarray,
    sample_rate: int = 16000,
    frame_length: int = 480,
    hop_length: int = 320,
    n_fft: int = 512,
    num_channels: int = 16,
    num_frames: int = 32,
    f_min: float = 50.0,
    f_max: float = 4000.0,
) -> np.ndarray:
    """
    Extract log-energy Mel-filterbank spectrogram of shape (num_channels, num_frames).

    Pipeline:
    1. Framing with Hann window (30 ms duration, 20 ms hop).
    2. Real FFT (512-pt) and power spectral density.
    3. 16-channel Mel triangular filterbank dot product.
    4. Logarithmic compression (dB scale).
    5. Truncate/pad to exact temporal dimension `num_frames`.

    Returns:
        np.ndarray of shape (16, num_frames) with float log energies.
    """
    waveform = np.asarray(waveform, dtype=np.float32)

    # Frame slicing
    total_samples = len(waveform)
    if total_samples < frame_length:
        # Pad with zeros if utterance is too short
        waveform = np.pad(waveform, (0, frame_length - total_samples), mode='constant')
        total_samples = len(waveform)

    num_total_frames = max(1, (total_samples - frame_length) // hop_length + 1)
    frames = np.zeros((num_total_frames, frame_length), dtype=np.float32)
    for t in range(num_total_frames):
        start = t * hop_length
        frames[t] = waveform[start : start + frame_length]

    # Apply Hann window: w(n) = 0.5 - 0.5 * cos(2*pi*n / (N-1))
    hann_window = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(frame_length) / (frame_length - 1))
    windowed_frames = frames * hann_window

    # 512-point Real FFT
    spectrum = np.fft.rfft(windowed_frames, n=n_fft, axis=-1)  # (num_total_frames, 257)
    power_spec = (np.abs(spectrum) ** 2) / float(n_fft)

    # Apply Mel filterbank
    filterbank = create_mel_filterbank(
        num_channels=num_channels,
        n_fft=n_fft,
        sample_rate=sample_rate,
        f_min=f_min,
        f_max=f_max,
    )
    # Shape: (num_total_frames, num_channels)
    mel_energies = np.dot(power_spec, filterbank.T)

    # Log compression: log10(E + eps)
    eps = 1e-6
    log_mel = np.log10(mel_energies + eps)  # (num_total_frames, num_channels)

    # Transpose to (num_channels, num_total_frames)
    spec = log_mel.T

    # Pad or truncate to exact target num_frames
    if spec.shape[1] < num_frames:
        pad_width = num_frames - spec.shape[1]
        spec = np.pad(spec, ((0, 0), (0, pad_width)), mode='constant', constant_values=np.min(spec))
    else:
        spec = spec[:, :num_frames]

    return spec


def quantize_spectrogram_to_uint8(
    log_mel_spec: np.ndarray,
    dyn_range_db: float = 60.0,
    silence_threshold_db: float = -30.0,
) -> np.ndarray:
    """
    Quantize floating-point log-Mel spectrogram to unsigned 8-bit integers [0, 255].
    Matches the input activation registers `a_i` driving the SCIM LFSR comparators.

    Dynamic Range Normalization & Silence Gating:
    - If peak energy is below `silence_threshold_db` relative to full scale,
      the entire frame is gated to 0.
    - Silicon Benefit: When activations are 0 (a_i = 0), the LFSR comparators generate
      zero 1s, Wallace tree toggling ceases, and dynamic switching power drops to 0 W!
    - For active speech, values within `dyn_range_db` of peak are mapped linearly to [0, 255].
    """
    max_val = np.max(log_mel_spec)
    
    # Silence gate: log10 power < -4.5 corresponds to -45 dB
    if max_val < (silence_threshold_db / 10.0):
        return np.zeros_like(log_mel_spec, dtype=np.uint8)

    min_val = max_val - (dyn_range_db / 10.0)  # in log10 domain, 10 dB = 1.0

    normalized = (log_mel_spec - min_val) / (max_val - min_val + 1e-9)
    clamped = np.clip(normalized, 0.0, 1.0)
    uint8_spec = np.round(clamped * 255.0).astype(np.uint8)
    return uint8_spec


def _deterministic_hash(s: str) -> int:
    """Deterministic integer hash independent of Python process hash randomization."""
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0x7FFFFFFF
    return h


def generate_synthetic_audio(
    keyword: str,
    duration_s: float = 1.0,
    sample_rate: int = 16000,
) -> np.ndarray:
    """
    Generate synthetic acoustic utterances for unit testing and bring-up verification.
    Keywords:
    - 'silence': White noise floor (-50 dB).
    - 'yes': Rising chirp 500 Hz -> 2200 Hz with vowel formant modulation.
    - 'no': Falling chirp 1800 Hz -> 400 Hz with nasal resonance.
    - 'stop': Sharp burst (1200 Hz) followed by broadband unvoiced fricative.
    - 'go': Low pitch onset (300 Hz) into sustained resonant vowel (900 Hz).
    - 'unknown': Dual steady-state harmonic tones (600 Hz + 1400 Hz) distinct from targets.
    """
    t = np.linspace(0.0, duration_s, int(sample_rate * duration_s), endpoint=False)
    rng = np.random.RandomState(_deterministic_hash(keyword))

    if keyword == 'silence':
        audio = rng.normal(0.0, 0.005, size=len(t))
    elif keyword == 'yes':
        # Rising chirp (500 -> 2200 Hz) enveloped in center
        envelope = np.exp(-((t - 0.45) ** 2) / (2.0 * (0.15**2)))
        f_t = 500.0 + 1700.0 * (t / duration_s)
        phase = 2.0 * np.pi * np.cumsum(f_t) / sample_rate
        audio = 0.5 * np.sin(phase) * envelope + rng.normal(0.0, 0.01, size=len(t))
    elif keyword == 'no':
        # Falling chirp (1800 -> 400 Hz)
        envelope = np.exp(-((t - 0.40) ** 2) / (2.0 * (0.18**2)))
        f_t = 1800.0 - 1400.0 * (t / duration_s)
        phase = 2.0 * np.pi * np.cumsum(f_t) / sample_rate
        audio = 0.5 * np.sin(phase) * envelope + rng.normal(0.0, 0.01, size=len(t))
    elif keyword == 'stop':
        # Plosive stop: burst at t=0.2s then 1200 Hz ring
        envelope = np.exp(-((t - 0.25) ** 2) / (2.0 * (0.08**2)))
        audio = 0.6 * np.sin(2.0 * np.pi * 1200.0 * t) * envelope
        # Fricative burst
        fricative = rng.normal(0.0, 0.2, size=len(t)) * np.exp(-((t - 0.5) ** 2) / (2.0 * (0.12**2)))
        audio = audio + fricative
    elif keyword == 'go':
        # Low frequency voiced vowel
        envelope = np.exp(-((t - 0.45) ** 2) / (2.0 * (0.22**2)))
        audio = 0.4 * np.sin(2.0 * np.pi * 320.0 * t) * envelope + 0.3 * np.sin(2.0 * np.pi * 880.0 * t) * envelope
        audio = audio + rng.normal(0.0, 0.01, size=len(t))
    else:
        # Unknown: Dual steady harmonic tones (600 Hz + 1400 Hz)
        envelope = np.exp(-((t - 0.5) ** 2) / (2.0 * (0.2**2)))
        audio = 0.35 * np.sin(2.0 * np.pi * 600.0 * t) * envelope + 0.35 * np.sin(2.0 * np.pi * 1400.0 * t) * envelope
        audio = audio + rng.normal(0.0, 0.01, size=len(t))

    # Normalize peak to 0.8 for active speech, preserve low noise for silence
    peak = np.max(np.abs(audio))
    if keyword != 'silence' and peak > 0:
        audio = 0.8 * (audio / peak)
    return audio.astype(np.float32)
