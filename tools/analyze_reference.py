"""Measure a reference WAV; retain reproducible JSON and a listening map.

Usage: python3 tools/analyze_reference.py out/reference/7mpiU85qMZg.wav
Tempo/key/section candidates are estimates, not a transcription.
"""
import json
import sys
from pathlib import Path

import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy.signal import find_peaks, welch


def analyze(path):
    pcm, sr = sf.read(path, always_2d=True)
    mono = pcm.mean(axis=1)
    rate, hop = 22050, 512
    y = librosa.resample(mono, orig_sr=sr, target_sr=rate)
    onset = librosa.onset.onset_strength(y=y, sr=rate, hop_length=hop)
    # Restrict to dance tempo range but also report half-time ambiguity.
    tempos = librosa.tempo_frequencies(len(onset), sr=rate, hop_length=hop)
    ac = librosa.autocorrelate(onset - onset.mean())
    selected = np.flatnonzero((tempos >= 125) & (tempos <= 180))
    lag = selected[np.argmax(ac[selected])]
    # Parabolic interpolation removes coarse hop-grid quantization.
    delta = 0.5 * (ac[lag-1] - ac[lag+1]) / (ac[lag-1] - 2*ac[lag] + ac[lag+1])
    tempo = 60 * rate / (hop * (lag + delta))
    _, beats = librosa.beat.beat_track(onset_envelope=onset, sr=rate,
                                      hop_length=hop, bpm=tempo)
    beat_times = librosa.frames_to_time(beats, sr=rate, hop_length=hop)
    harmonic, _ = librosa.effects.hpss(y)
    chroma = librosa.feature.chroma_stft(y=harmonic, sr=rate, hop_length=hop)
    pitch = chroma.mean(axis=1)
    profiles = {
        "major": np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]),
        "minor": np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17]),
    }
    names = ["C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"]
    keys = sorted([dict(key=f"{names[k]} {mode}", correlation=float(np.corrcoef(pitch, np.roll(p, k))[0,1]))
                   for mode,p in profiles.items() for k in range(12)],
                  key=lambda x: x["correlation"], reverse=True)
    rms = np.array([np.sqrt(np.mean(pcm[i:i+sr]**2)) for i in range(0,len(pcm),sr)])
    rms_db = 20*np.log10(np.maximum(rms,1e-9))
    f, power = welch(pcm, fs=sr, nperseg=8192, axis=0)
    power = power.sum(axis=1)
    bands = {f"{a}-{b} Hz": float(100*power[(f>=a)&(f<b)].sum()/power.sum())
             for a,b in [(20,120),(120,1000),(1000,3000),(3000,8000),(8000,sr/2)]}
    from scipy.signal import butter, sosfilt
    stereo_low = sosfilt(butter(4,120,fs=sr,output="sos"),pcm,axis=0)
    mid, side = pcm.mean(axis=1), (pcm[:,0]-pcm[:,-1])/2
    # Six-second texture windows; novelty compares means on either side.
    spec = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
    mfcc = librosa.feature.mfcc(S=librosa.power_to_db(spec**2), sr=rate, n_mfcc=13)
    features = np.vstack([mfcc, chroma*30])
    frames = int(6*rate/hop)
    novelty = np.zeros(features.shape[1])
    scale = features.std(axis=1) + 1e-6
    for i in range(frames, features.shape[1]-frames):
        novelty[i] = np.sqrt(np.mean(((features[:,i:i+frames].mean(axis=1) -
                                     features[:,i-frames:i].mean(axis=1))/scale)**2))
    peaks, _ = find_peaks(novelty, distance=int(10*rate/hop), prominence=0.15)
    peaks = sorted(peaks, key=lambda p: novelty[p], reverse=True)[:12]
    boundaries = sorted([dict(seconds=round(float(p*hop/rate),2), novelty=round(float(novelty[p]),3))
                         for p in peaks], key=lambda p:p["seconds"])
    duration = len(pcm)/sr
    report = dict(source=str(path), duration_seconds=duration, sample_rate=sr,
                  channels=pcm.shape[1], finite=bool(np.isfinite(pcm).all()),
                  tempo_bpm=round(float(tempo),2), half_time_bpm=round(float(tempo/2),2),
                  tempo_method="onset autocorrelation, 125-180 BPM search; interpolated peak",
                  key_candidates=keys[:5], key_method="HPSS harmonic chroma, Krumhansl profile correlation",
                  sample_peak_dbfs=float(20*np.log10(np.max(np.abs(pcm)))),
                  rms_dbfs=float(20*np.log10(np.sqrt(np.mean(pcm**2)))),
                  active_one_second_rms_percentiles_dbfs={str(p):float(np.percentile(rms_db[rms_db>-45],p)) for p in (10,50,90)},
                  spectral_energy_percent=bands,
                  stereo_correlation=float(np.corrcoef(pcm.T)[0,1]),
                  bass_stereo_correlation_below_120hz=float(np.corrcoef(stereo_low.T)[0,1]),
                  side_to_mid_db=float(10*np.log10(np.mean(side**2)/np.mean(mid**2))),
                  texture_change_candidates=boundaries,
                  caveats=["Making Of upload, not necessarily the album master.",
                           "Key and texture boundaries are automated estimates; no instrument or chord transcription.",
                           "Tempo can be perceived at half time. WAV is decoded lossy YouTube audio."])
    path.with_suffix(".analysis.json").write_text(json.dumps(report,indent=2)+"\n")
    np.savetxt(path.with_suffix(".beats.csv"), beat_times, header="seconds", delimiter=",")
    fig, axes = plt.subplots(4,1,figsize=(15,11),sharex=True,layout="constrained")
    axes[0].plot(np.arange(len(rms_db)),rms_db,color="#185c47")
    axes[0].set(ylabel="RMS dBFS",ylim=(-50,0),title=f"{path.stem}: {duration:.1f}s | estimated {tempo:.1f} BPM | key candidate {keys[0]['key']}")
    axes[1].imshow(librosa.amplitude_to_db(spec,ref=np.max),origin="lower",aspect="auto",
                   extent=[0,duration,0,rate/2],vmin=-65,vmax=0,cmap="magma")
    axes[1].set(ylabel="Frequency Hz",ylim=(0,8000))
    axes[2].imshow(chroma,origin="lower",aspect="auto",extent=[0,duration,-0.5,11.5],cmap="viridis")
    axes[2].set_yticks(range(12),names)
    axes[2].set_ylabel("Pitch class")
    axes[3].plot(np.arange(len(novelty))*hop/rate,novelty,color="#6e4ca2")
    axes[3].set(ylabel="Texture novelty",xlabel="Seconds")
    for a in axes:
        for b in boundaries:
            a.axvline(b["seconds"],color="#888888",alpha=0.4,linewidth=0.7)
        a.set_xlim(0,duration)
    fig.savefig(path.with_suffix(".analysis.png"),dpi=140)
    plt.close(fig)
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    analyze(Path(sys.argv[1]))
