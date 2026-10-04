"""Focused DSP regression checks: python3 -m unittest discover -s tools -p 'test_*.py'."""
import unittest
import numpy as np
from scipy.signal import periodogram
from psy import dsp, instruments as ins
from psy.mycelium import Mycelium
from psy.journey import Journey


class AudioTests(unittest.TestCase):
    def test_width_preserves_mono_and_bass(self):
        t = dsp.secs(dsp.SR)
        bass = np.sin(2 * np.pi * 50 * t)
        detail = np.sin(2 * np.pi * 1500 * t) * 0.2
        x = np.stack([bass + detail, bass - detail], axis=1)
        y = dsp.stereo_width(x, 2)
        np.testing.assert_allclose(y.mean(1), x.mean(1), atol=1e-14)
        self.assertGreater(np.std((y[:, 0] - y[:, 1])[1000:]), 1.8 * np.std((x[:, 0] - x[:, 1])[1000:]))
        centered = np.stack([bass, bass], axis=1)
        np.testing.assert_allclose(dsp.stereo_width(centered, 2), centered, atol=1e-14)

    def test_room_reaches_both_channels_and_preserves_tail(self):
        x = np.zeros((dsp.SR, 2))
        x[0, 0] = 1
        ir = dsp.room_ir(0.4, 0.01, 5)
        y = dsp.spatial_reverb(x, ir)
        self.assertTrue(np.isfinite(y).all())
        self.assertGreater(np.linalg.norm(y[:, 1]), 0.2)
        self.assertLess(np.max(np.abs(y[:int(0.01 * dsp.SR)])), 1e-12)
        self.assertGreater(np.linalg.norm(y[int(0.1 * dsp.SR):]), 0.01)
        self.assertGreater(np.linalg.norm(y.mean(1)), 0.1)

    def test_echo_preserves_first_direction_then_alternates(self):
        x = np.zeros((dsp.SR * 2, 2)); x[0, 1] = 1
        y = dsp.tempo_echo(x, [0, 2, 4], taps=2)
        first = int(0.375 * dsp.SR)
        second = int(0.75 * dsp.SR)
        self.assertGreater(np.linalg.norm(y[first:first + 100, 1]), 0.1)
        self.assertLess(np.linalg.norm(y[first:first + 100, 0]), 1e-12)
        self.assertGreater(np.linalg.norm(y[second:second + 100, 0]), 0.03)
        self.assertLess(np.max(np.abs(y[:first])), 1e-12)

    def test_echo_follows_tempo_change(self):
        x = np.zeros((dsp.SR * 5, 2)); x[int(2.0 * dsp.SR), 0] = 1
        y = dsp.tempo_echo(x, [0, 2, 3.6, 5.2], taps=1)
        # Source at bar 1: 0.75 beats later at 150 BPM, or 0.3 seconds.
        peak = np.argmax(np.abs(y[:, 0])) / dsp.SR
        self.assertAlmostEqual(peak, 2.3, delta=0.002)

    def test_oud_fractional_tuning_and_stability(self):
        for midi in (52, 57, 64, 69):
            y = ins.oud(midi, 0.8, np.random.default_rng(9))
            self.assertTrue(np.isfinite(y).all())
            self.assertLessEqual(np.max(np.abs(y)), 1.001)
            f, p = periodogram(y[int(0.08 * dsp.SR):], dsp.SR, nfft=262144)
            hz = dsp.midi_hz(midi)
            region = (f > hz * 0.95) & (f < hz * 1.05)
            measured = f[region][np.argmax(p[region])]
            cents = 1200 * np.log2(measured / hz)
            self.assertLess(abs(cents), 6, (midi, cents))

    def test_flute_silence_and_seed(self):
        empty = ins.ney_phrase([], 1000, np.random.default_rng(4))
        self.assertTrue(np.all(empty == 0))
        notes = [(0, dsp.SR, 64, False), (dsp.SR, dsp.SR, 65, True)]
        a = ins.ney_phrase(notes, dsp.SR * 3, np.random.default_rng(4))
        b = ins.ney_phrase(notes, dsp.SR * 3, np.random.default_rng(4))
        np.testing.assert_array_equal(a, b)
        self.assertTrue(np.isfinite(a).all())
        self.assertLess(np.max(np.abs(a[-1000:])), 1e-9)

    def test_score_has_breath_spaces_and_stable_seed(self):
        a, b = Mycelium(), Mycelium()
        self.assertEqual(a.melody, b.melody)
        for bar, beat, length, *_ in a.melody:
            self.assertGreater(length, 0)
            if a.rows[bar]["i"] % 8 == 7:
                self.assertLessEqual(beat + length, 2.5)

    def test_short_render_both_effect_paths(self):
        # Exercise all layers, send routing, tails and master with a second seed.
        for engine in (Journey, Mycelium):
            chapter = dict(engine.CHAPTERS[1], bars=12, e=[(0, 0.4), (1, 0.7)],
                           carriers=["ney", "duet"], logs=True)
            short = type("Short", (engine,), dict(CHAPTERS=[chapter], RISES={},
                         SWELL_AT=(), FALLS=()))
            y = short(seed=9).render(log=lambda *a: None)
            self.assertTrue(np.isfinite(y).all(), engine.__name__)
            self.assertEqual(y.shape[1], 2)
            self.assertGreater(np.sqrt(np.mean(y*y)), 0.02)
            self.assertLessEqual(np.max(np.abs(y)), 0.930001)



class SpaceTests(unittest.TestCase):
    def test_lufs_reference_tone(self):
        # BS.1770: a full-scale 997 Hz sine in one channel reads about -3.0 LUFS.
        x = np.zeros((dsp.SR * 3, 2))
        x[:, 0] = np.sin(2 * np.pi * 997 * dsp.secs(dsp.SR * 3))
        self.assertAlmostEqual(dsp.lufs(x), -3.0, delta=0.3)

    def test_fdn_is_dense_decorrelated_and_decays(self):
        x = np.zeros((dsp.SR * 4, 2)); x[0] = 1
        y = dsp.fdn_reverb(x, rt60=2.0, seed=1)
        self.assertTrue(np.isfinite(y).all())
        self.assertLess(abs(np.corrcoef(y[:, 0], y[:, 1])[0, 1]), 0.2)
        early = np.mean(y[int(0.1 * dsp.SR):int(0.3 * dsp.SR)] ** 2)
        late = np.mean(y[int(2.0 * dsp.SR):int(2.2 * dsp.SR)] ** 2)
        self.assertGreater(10 * np.log10(early / late), 45)

    def test_stage_direction_and_distance(self):
        rng = np.random.default_rng(0)
        x = np.repeat(rng.standard_normal((dsp.SR, 1)) * 0.1, 2, axis=1)
        right = dsp.stage(x, 60, 0.0)
        self.assertGreater(np.std(right[:, 1]), 1.5 * np.std(right[:, 0]))
        near = dsp.stage(x, 0, 0.1, room=Mycelium.ROOM)
        far = dsp.stage(x, 0, 0.9, room=Mycelium.ROOM)
        self.assertLess(np.std(far), np.std(near))
        # far sources are wetter: less correlated with the dry signal
        c = lambda y: np.corrcoef(y.mean(1), x[:, 0])[0, 1]
        self.assertLess(c(far), c(near))

    def test_drive_oversampling_reduces_aliasing(self):
        n = dsp.SR
        s = np.sin(2 * np.pi * 1567 * dsp.secs(n))
        fr = np.fft.rfftfreq(n, 1 / dsp.SR)
        harm = np.zeros(len(fr), bool)
        for k in range(1, 40):
            harm |= np.abs(fr - k * 1567) < 3
        def alias(y):
            S = np.abs(np.fft.rfft(y * np.hanning(n))) ** 2
            return S[~harm].sum() / S[harm].sum()
        self.assertLess(alias(dsp.drive(s, 3, os=2)), alias(dsp.drive(s, 3, os=1)) / 10)


if __name__ == "__main__":
    unittest.main()
