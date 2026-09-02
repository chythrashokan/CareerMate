from django.test import TestCase
from .audio_analysis import compute_shiver_penalty, lip_movement_score, grammar_suggestions_and_score, compute_normalized_confidence, compute_pause_penalty, compute_hesitation_penalty, compute_stuck_penalty

class AudioAnalysisUnitTests(TestCase):
    def test_shiver_from_durations(self):
        durs = [0.12, 0.14, 0.11, 0.13, 0.12]
        p = compute_shiver_penalty(durs)
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 0.4)

    def test_lip_score_empty(self):
        s = lip_movement_score([])
        self.assertAlmostEqual(s, 0.5, delta=0.01)

    def test_grammar_heuristic(self):
        sug, sc = grammar_suggestions_and_score('This is a sentence with repeating repeating words and a veryverylongwordssssssssssss')
        self.assertIsInstance(sug, list)
        self.assertGreaterEqual(sc, 0.0)
        self.assertLessEqual(sc, 1.0)

    def test_normalized_confidence_behaviour(self):
        n = compute_normalized_confidence(asr_confidence=90, model_confidence=80, clarity_score=70, grammar_score=0.9, shiver_penalty=0.0, lip_score=0.9)
        self.assertGreater(n, 0.6)

    def test_pause_penalty(self):
        # A few long pauses should yield a non-zero penalty up to 0.3
        pauses = [200, 700, 1500, 1200, 2500]
        p = compute_pause_penalty(pauses, long_pause_ms=1000)
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 0.3)

    def test_hesitation_penalty(self):
        p = compute_hesitation_penalty(filler_word_count=5, words_per_minute=50)
        self.assertGreater(p, 0)
        self.assertLessEqual(p, 0.2)

    def test_stuck_penalty(self):
        p = compute_stuck_penalty(restart_attempts=2, repeated_words=3)
        self.assertGreater(p, 0)
        self.assertLessEqual(p, 0.2)

    def test_penalties_reduce_normalized_confidence(self):
        base = compute_normalized_confidence(asr_confidence=90, model_confidence=80, clarity_score=70, grammar_score=0.9, shiver_penalty=0.0, lip_score=0.9)
        with_penalties = compute_normalized_confidence(asr_confidence=90, model_confidence=80, clarity_score=70, grammar_score=0.9, shiver_penalty=0.02, lip_score=0.9, pause_penalty=0.05, hesitation_penalty=0.05, stuck_penalty=0.03)
        self.assertLess(with_penalties, base)
