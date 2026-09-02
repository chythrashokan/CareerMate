"""
Audio and text analysis utilities for Interview Simulator
- Shivering (jitter) detection
- Lip movement scoring (from viseme sequences)
- Grammar suggestions (using language_tool_python when available)
- Normalized confidence calculation combining ASR confidence, AI scores, grammar and audio signals

These are heuristic implementations intended to be safe when optional dependencies aren't available.
"""

import math
import statistics
import logging

logger = logging.getLogger(__name__)

# Try to import language_tool_python for grammar checking; if not available, fall back to lightweight heuristics
try:
    import language_tool_python
    _LT_AVAILABLE = True
except Exception:
    _LT_AVAILABLE = False

NEUTRAL_VISEMES = set(['neutral', 'closed', 'rest', 'sil'])


def compute_shiver_penalty(phoneme_durations=None, confidence_history=None):
    """Compute a shivering/jitter penalty.

    Prefer phoneme durations if provided, otherwise use confidence_history (stddev) as a proxy.
    Returns penalty in [0.0, 0.4].
    """
    try:
        # Use phoneme durations if available (more accurate when phoneme timing is provided)
        durations = [float(d) for d in (phoneme_durations or []) if d is not None]
        if len(durations) >= 3:
            mean = statistics.mean(durations)
            stdev = statistics.pstdev(durations)
            if mean <= 0:
                return 0.0
            jitter = stdev / mean  # relative jitter
            penalty = (jitter - 0.12) / 1.0
            penalty = max(0.0, min(penalty, 0.4))
            return round(penalty, 3)

        # Otherwise use confidence history standard deviation as a proxy
        confs = [float(c) for c in (confidence_history or []) if c is not None]
        if len(confs) < 3:
            return 0.0
        sd = statistics.pstdev(confs)
        # Map sd to penalty; small sd -> 0, large sd -> up to 0.4
        penalty = (sd - 0.09) * 1.2
        penalty = max(0.0, min(penalty, 0.4))
        return round(penalty, 3)
    except Exception as e:
        logger.exception('Error computing shiver penalty: %s', e)
        return 0.0

def compute_pause_penalty(pause_history=None, long_pause_ms=1000):
    """Compute a pause penalty from pause history (list of pause durations in ms).

    Penalize frequent or very long pauses. Returns penalty in [0.0, 0.3].
    """
    try:
        pauses = [float(p) for p in (pause_history or []) if p is not None]
        if not pauses:
            return 0.0
        long_pauses = [p for p in pauses if p >= long_pause_ms]
        ratio = len(long_pauses) / max(1, len(pauses))
        max_pause = max(pauses)
        # base penalty from ratio of long pauses
        penalty = min(0.25, ratio * 0.25)
        # small additional penalty for extremely long single pause
        if max_pause > 3000:
            penalty += min(0.05, (max_pause - 3000) / 10000.0)
        penalty = max(0.0, min(0.3, penalty))
        return round(penalty, 3)
    except Exception as e:
        logger.exception('Error computing pause penalty: %s', e)
        return 0.0


def compute_hesitation_penalty(filler_word_count=0, words_per_minute=None):
    """Compute a hesitation penalty using filler words count and speech rate.

    Returns penalty in [0.0, 0.2]. Filler words add a small penalty; very slow WPM adds more.
    """
    try:
        penalty = 0.0
        if filler_word_count and filler_word_count > 0:
            penalty += min(0.12, filler_word_count * 0.02)
        if words_per_minute is not None:
            wpm = float(words_per_minute)
            # If speaking rate is too slow (<60 WPM), add penalty up to 0.08
            if wpm < 60:
                penalty += min(0.08, (60 - wpm) / 200.0)
        return round(max(0.0, min(0.2, penalty)), 3)
    except Exception as e:
        logger.exception('Error computing hesitation penalty: %s', e)
        return 0.0


def compute_stuck_penalty(restart_attempts=0, repeated_words=0):
    """Compute a penalty for being stuck/restarting or repeating phrases.

    Returns penalty in [0.0, 0.2]. More restarts / repeated patterns => higher penalty.
    """
    try:
        penalty = 0.0
        if restart_attempts and restart_attempts > 0:
            penalty += min(0.15, restart_attempts * 0.05)
        if repeated_words and repeated_words > 0:
            penalty += min(0.1, repeated_words * 0.03)
        return round(max(0.0, min(0.2, penalty)), 3)
    except Exception as e:
        logger.exception('Error computing stuck penalty: %s', e)
        return 0.0

def lip_movement_score(viseme_sequence):
    """Estimate a lip movement score 0..1 from viseme sequence.

    Accepts either a list of strings (viseme names) or list of dicts with 'viseme' key.
    Score is the fraction of non-neutral visemes weighted by diversity.
    """
    try:
        visemes = []
        for v in (viseme_sequence or []):
            if isinstance(v, dict):
                vis = v.get('viseme') or v.get('label')
            else:
                vis = v
            if vis is None:
                continue
            visemes.append(str(vis).lower())

        if not visemes:
            return 0.5  # unknown but not terrible

        active = [v for v in visemes if v not in NEUTRAL_VISEMES]
        active_ratio = len(active) / len(visemes)
        diversity = len(set(active)) / max(1, len(active))
        score = 0.6 * active_ratio + 0.4 * diversity
        return round(max(0.0, min(1.0, score)), 3)
    except Exception as e:
        logger.exception('Error computing lip movement score: %s', e)
        return 0.5


def grammar_suggestions_and_score(text, max_suggestions=5):
    """Return grammar suggestions and a grammar score (0..1) where 1 means no errors.

    If language_tool_python is available, use it; otherwise, run lightweight heuristics.
    """
    try:
        if not text:
            return [], 1.0

        if _LT_AVAILABLE:
            try:
                tool = language_tool_python.LanguageTool('en-US')
                matches = tool.check(text)
                errors = [m for m in matches if m.ruleId != 'UPPERCASE_SENTENCE_START']
                suggestions = []
                for m in errors[:max_suggestions]:
                    suggestions.append({'message': m.message, 'suggestions': m.replacements[:3], 'offset': m.offset, 'length': m.errorLength})
                # grammar_score: 1 - (errors normalized by sentence count)
                sentence_count = max(1, text.count('.') + text.count('!') + text.count('?'))
                error_count = len(errors)
                score = 1.0 - min(1.0, error_count / (3.0 * sentence_count))
                return suggestions, round(max(0.0, min(1.0, score)), 3)
            except Exception as e:
                logger.exception('LanguageTool check failed: %s', e)
                # fall through to heuristic

        # Lightweight heuristic fallback: detect long sentences and repeated words
        words = [w.strip(',.!?;:').lower() for w in text.split()]
        repeated_pairs = sum(1 for i in range(len(words)-1) if words[i] == words[i+1])
        long_sentences = sum(1 for s in text.split('.') if len(s.split()) > 40)
        suggestions = []
        if repeated_pairs:
            suggestions.append({'message': 'Repeated word detected', 'examples': words[:5]})
        if long_sentences:
            suggestions.append({'message': 'One or more long sentences; try splitting for clarity', 'examples': []})
        score = 1.0 - min(0.6, (repeated_pairs * 0.2 + long_sentences * 0.2))
        return suggestions[:max_suggestions], round(max(0.0, min(1.0, score)), 3)

    except Exception as e:
        logger.exception('Error computing grammar suggestions: %s', e)
        return [], 1.0


def compute_asr_confidence_from_history(confidence_history=None, audio_levels=None):
    """Estimate a robust ASR confidence (0..1) from confidence_history and optional audio_levels.

    - confidence_history: recent ASR confidences in 0..1 range
    - audio_levels: recent audio levels 0..1 to bias low when audio was very quiet
    """
    try:
        confs = [float(c) for c in (confidence_history or []) if c is not None]
        confs = [c for c in confs if c > 0]
        if confs:
            avg = sum(confs) / len(confs)
        else:
            avg = None

        # audio level influence
        audio_mean = None
        if audio_levels:
            a = [float(a) for a in audio_levels if a is not None]
            if a:
                audio_mean = sum(a) / len(a)

        if avg is None and audio_mean is None:
            return None

        if avg is None:
            # estimate from audio level
            return round(max(0.0, min(1.0, 0.6 * (audio_mean or 0) + 0.4)), 3)

        if audio_mean is None:
            return round(max(0.0, min(1.0, avg)), 3)

        # Weighted combination
        combined = 0.8 * avg + 0.2 * audio_mean
        return round(max(0.0, min(1.0, combined)), 3)
    except Exception as e:
        logger.exception('Error computing ASR confidence from history: %s', e)
        return None


def compute_normalized_confidence(asr_confidence=None, model_confidence=None, clarity_score=None, grammar_score=1.0, shiver_penalty=0.0, lip_score=0.8, pause_penalty=0.0, hesitation_penalty=0.0, stuck_penalty=0.0, emotion_data=None, dominant_emotion=None):
    """Combine multiple signals into a normalized confidence 0..1.

    - asr_confidence: can be 0..1 or 0..100
    - model_confidence: AI evaluation confidence 0..100 or 0..1
    - clarity_score: 0..100 or 0..1
    - grammar_score: 0..1
    - shiver_penalty: 0..0.4
    - lip_score: 0..1
    - pause_penalty / hesitation_penalty / stuck_penalty: additional penalties applied from audio analysis
    - emotion_data: dict or JSON str with emotion probabilities
    - dominant_emotion: str with dominant emotion name

    Weighting strategy (heuristic): prefer ASR where available, then model clarity. Penalties are subtracted at the end.
    Emotion is incorporated as a modulator of final confidence.
    """
    try:
        # Normalize inputs to 0..1
        def norm(v):
            if v is None:
                return None
            try:
                v = float(v)
            except Exception:
                return None
            if v > 1:
                v = v / 100.0
            return max(0.0, min(1.0, v))

        asr = norm(asr_confidence)
        mc = norm(model_confidence)
        cl = norm(clarity_score)

        # baseline: prefer asr if available, otherwise model confidence, else 0.6
        if asr is not None:
            base = 0.75 * asr + 0.25 * (mc if mc is not None else 0.6)
        elif mc is not None:
            base = 0.7 * mc + 0.3 * (cl if cl is not None else 0.6)
        else:
            base = 0.6

        # Apply grammar influence (improves confidence slightly) and lip movement multiplier
        base = base * (0.85 + 0.15 * grammar_score)
        base = base * (0.7 + 0.3 * lip_score)

        # Apply emotion modulation (20% influence on final score)
        emotion_conf = compute_emotion_confidence(emotion_data, dominant_emotion)
        base = base * (0.8 + 0.2 * emotion_conf)

        # Combine penalties
        total_penalty = sum(float(p) for p in (shiver_penalty, pause_penalty, hesitation_penalty, stuck_penalty) if p is not None)
        final = base - total_penalty
        final = max(0.0, min(1.0, final))
        return round(final, 3)
    except Exception as e:
        logger.exception('Error computing normalized confidence: %s', e)
        return 0.6


def compute_emotion_confidence(emotion_data=None, dominant_emotion=None):
    """Compute confidence score from face emotion analysis.
    
    Args:
        emotion_data: dict or JSON str with emotion probabilities (e.g., {'happy': 0.8, 'neutral': 0.15, ...})
        dominant_emotion: str, the dominant emotion detected (e.g., 'happy', 'neutral', 'angry')
    
    Returns:
        float: confidence score 0..1 based on emotion
    
    Reasoning:
    - Positive emotions (happy, neutral, calm) boost confidence
    - Negative emotions (angry, fear, disgust, sad) reduce confidence
    - Neutral emotion is baseline
    """
    try:
        # Parse emotion_data if it's a JSON string
        if isinstance(emotion_data, str):
            import json
            emotion_data = json.loads(emotion_data)
        
        if not emotion_data or not isinstance(emotion_data, dict):
            emotion_data = {}
        
        # Map emotions to confidence weights
        # Positive emotions boost, negative emotions penalize
        emotion_weights = {
            'happy': 1.0,      # Confident, engaging
            'neutral': 0.7,    # Baseline, composed
            'calm': 0.85,      # Confident and controlled
            'surprise': 0.6,   # Can indicate uncertainty
            'sad': 0.4,        # Low engagement, low confidence
            'angry': 0.3,      # Negative, aggressive
            'fear': 0.2,       # Anxious, not confident
            'disgust': 0.25,   # Negative emotion
        }
        
        # If we have emotion probabilities, compute weighted average
        if emotion_data:
            total_weight = 0.0
            weighted_sum = 0.0
            for emotion, probability in emotion_data.items():
                prob = float(probability) if probability is not None else 0.0
                weight = emotion_weights.get(emotion.lower(), 0.5)  # default 0.5 for unknown
                weighted_sum += prob * weight
                total_weight += prob
            
            if total_weight > 0:
                emotion_conf = weighted_sum / total_weight
            else:
                emotion_conf = 0.7  # neutral baseline
        elif dominant_emotion:
            # If only dominant emotion is provided, use its weight directly
            emotion_conf = emotion_weights.get(dominant_emotion.lower(), 0.7)
        else:
            # No emotion data available, use neutral baseline
            emotion_conf = 0.7
        
        return round(max(0.0, min(1.0, emotion_conf)), 3)
    except Exception as e:
        logger.exception('Error computing emotion confidence: %s', e)
        return 0.7  # neutral baseline on error

def compute_audio_emotion_confidence(phoneme_durations=None, confidence_history=None, audio_levels=None, speaking_duration=None):
    """Compute emotion confidence from audio characteristics.
    
    Audio emotions indicate emotional state through:
    - Phoneme/speaking consistency (smooth vs. jittery = calm vs. anxious)
    - Confidence stability (consistent vs. fluctuating = confident vs. uncertain)
    - Audio levels (strong vs. weak = engaged vs. disengaged)
    - Speaking duration (long fluent vs. choppy = calm vs. stressed)
    
    Args:
        phoneme_durations: list of phoneme durations (smoothness indicator)
        confidence_history: list of ASR/speech confidence scores over time
        audio_levels: list of audio amplitude levels over time
        speaking_duration: total speaking duration in seconds
    
    Returns:
        float: emotion confidence 0..1 based on audio quality indicators
    """
    try:
        emotion_score = 0.7  # baseline neutral
        indicators = 0
        
        # 1. Phoneme consistency = calmness/smoothness
        # Lower variance in phoneme durations = calm, smooth delivery
        if phoneme_durations and len(phoneme_durations) >= 3:
            try:
                durations = [float(d) for d in phoneme_durations if d is not None]
                if len(durations) >= 3:
                    mean_dur = statistics.mean(durations)
                    if mean_dur > 0:
                        jitter = statistics.pstdev(durations) / mean_dur
                        # Low jitter (smooth) = higher emotion score (calm, confident)
                        # High jitter (shaky) = lower emotion score (anxious, uncertain)
                        smoothness = max(0.0, 1.0 - (jitter * 2))  # map to 0..1
                        emotion_score += smoothness * 0.3  # 30% weight
                        indicators += 1
            except Exception as e:
                logger.debug('Error computing phoneme smoothness: %s', e)
        
        # 2. Confidence stability = self-assurance
        # Stable confidence over time = assured, confident
        # Fluctuating confidence = uncertain, nervous
        if confidence_history and len(confidence_history) >= 3:
            try:
                confs = [float(c) for c in confidence_history if c is not None and 0 <= float(c) <= 1]
                if len(confs) >= 3:
                    conf_mean = statistics.mean(confs)
                    conf_stdev = statistics.pstdev(confs)
                    # Low variance = stable = confident
                    stability = max(0.0, 1.0 - conf_stdev)  # 0..1 scale
                    # Also boost if mean confidence is high
                    overall_conf = (conf_mean + stability) / 2
                    emotion_score += overall_conf * 0.4  # 40% weight
                    indicators += 1
            except Exception as e:
                logger.debug('Error computing confidence stability: %s', e)
        
        # 3. Audio energy = engagement/enthusiasm
        # Strong consistent audio = engaged, enthusiastic
        # Weak/dropping audio = disengaged, low energy
        if audio_levels and len(audio_levels) >= 3:
            try:
                levels = [float(l) for l in audio_levels if l is not None]
                if len(levels) >= 3:
                    level_mean = statistics.mean(levels)
                    level_max = max(levels)
                    if level_max > 0:
                        # Normalize to 0..1 (normalized levels)
                        energy = min(1.0, level_mean / level_max)
                        emotion_score += energy * 0.2  # 20% weight
                        indicators += 1
            except Exception as e:
                logger.debug('Error computing audio energy: %s', e)
        
        # 4. Speaking duration quality
        # Optimal: 10-60 seconds per answer (engaged, thorough)
        # Too short (<5 sec) = disengaged, minimal effort
        # Extremely long (>120 sec) = nervous rambling
        if speaking_duration and speaking_duration > 0:
            try:
                dur = float(speaking_duration)
                if 5 <= dur <= 60:
                    # Optimal range = high engagement
                    duration_score = 0.9
                elif dur < 5:
                    # Too short = low engagement
                    duration_score = 0.4
                elif 60 < dur <= 120:
                    # Long but controlled = engaged
                    duration_score = 0.75
                else:
                    # Extremely long = nervous
                    duration_score = 0.5
                emotion_score += duration_score * 0.1  # 10% weight
                indicators += 1
            except Exception as e:
                logger.debug('Error computing duration score: %s', e)
        
        # Average the indicators
        if indicators > 0:
            emotion_score = emotion_score / (indicators + 1)  # +1 for baseline
        
        return round(max(0.0, min(1.0, emotion_score)), 3)
        
    except Exception as e:
        logger.exception('Error computing audio emotion confidence: %s', e)
        return 0.7  # neutral baseline on error


def compute_combined_emotion_confidence(face_emotion_data=None, face_dominant_emotion=None, 
                                       phoneme_durations=None, confidence_history=None, 
                                       audio_levels=None, speaking_duration=None):
    """Compute combined emotion confidence from BOTH face AND audio analysis.
    
    Combines:
    - Face emotion (visual/facial expressions): 60% weight
    - Audio emotion (voice characteristics): 40% weight
    
    Args:
        face_emotion_data: dict of emotion probabilities from DeepFace
        face_dominant_emotion: string of dominant emotion from face
        phoneme_durations: list of phoneme durations
        confidence_history: list of confidence scores
        audio_levels: list of audio amplitude levels
        speaking_duration: total speaking duration
    
    Returns:
        dict with:
            - combined_emotion_confidence: 0..1 overall emotion score
            - face_emotion_confidence: 0..1 face-based score
            - audio_emotion_confidence: 0..1 audio-based score
            - dominant_emotion: string from face analysis
    """
    try:
        # Compute face emotion (60% weight)
        face_emotion_conf = compute_emotion_confidence(
            emotion_data=face_emotion_data,
            dominant_emotion=face_dominant_emotion
        )
        
        # Compute audio emotion (40% weight)
        audio_emotion_conf = compute_audio_emotion_confidence(
            phoneme_durations=phoneme_durations,
            confidence_history=confidence_history,
            audio_levels=audio_levels,
            speaking_duration=speaking_duration
        )
        
        # Combine: 60% face + 40% audio
        combined_emotion_conf = (face_emotion_conf * 0.6) + (audio_emotion_conf * 0.4)
        
        return {
            'combined_emotion_confidence': round(combined_emotion_conf, 3),
            'face_emotion_confidence': round(face_emotion_conf, 3),
            'audio_emotion_confidence': round(audio_emotion_conf, 3),
            'dominant_emotion': face_dominant_emotion or 'neutral'
        }
        
    except Exception as e:
        logger.exception('Error computing combined emotion confidence: %s', e)
        return {
            'combined_emotion_confidence': 0.7,
            'face_emotion_confidence': 0.7,
            'audio_emotion_confidence': 0.7,
            'dominant_emotion': 'neutral'
        }