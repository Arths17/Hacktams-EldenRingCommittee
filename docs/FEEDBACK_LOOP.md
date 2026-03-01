# Feedback Learning Loop — HealthOS AI

## Overview

The **Feedback Learning Loop** enables HealthOS AI to dynamically adapt protocol recommendations based on user-reported outcomes. When a user reports feedback (e.g., "my energy improved" or "still feeling anxious"), the system:

1. **Extracts** signal keywords and sentiment from natural language
2. **Updates** per-user protocol weights using Bayesian-style learning
3. **Re-ranks** protocols with learned weights for the next recommendation cycle
4. **Persists** learned weights to disk for long-term user modeling

---

## Architecture

### Layer 1: Base Protocol Weights (`user_state.py`, lines 50–90)

30 health protocols with baseline importance scores (0.40–0.90):

```python
PROTOCOL_WEIGHTS = {
    "sleep_protocol":              0.90,  # Sleep is foundational
    "stress_protocol":             0.85,
    "energy_protocol":             0.80,
    "mood_protocol":               0.75,
    # ... 26 more protocols
}
```

### Layer 2: Signal-to-Protocol Mapping (`user_state.py`, lines 716–733)

Maps user feedback signals to affected protocols:

```python
FEEDBACK_PROTOCOL_MAP = {
    "energy":   ["energy_protocol", "b_complex_protocol", "electrolyte_protocol"],
    "focus":    ["cognitive_protocol", "omega_protocol", "blood_sugar_protocol"],
    "sleep":    ["sleep_protocol"],
    "stress":   ["stress_protocol", "gut_protocol", "anti_inflammatory_protocol"],
    # ... 10 more signals
}
```

### Layer 3: Pattern Extraction (`user_state.py`, lines 738–755)

Six regex patterns capture different feedback styles:

| Pattern | Example | Extracted Signal |
|---------|---------|------------------|
| **Explicit** | "energy: +2" | `{"energy": 2.0}` |
| **Improved** | "my sleep improved" | `{"sleep": 1.0}` |
| **Worsened** | "stress is worse" | `{"stress": -1.0}` |
| **Pos Adj** | "more energetic" | `{"energy": 1.0}` |
| **Neg Adj** | "less tired" / "more anxious" | `{"energy": 1.0}` / `{"anxiety": -1.0}` |
| **Standalone** | "feeling anxious" | `{"anxiety": -1.0}` |

### Layer 4: Weight Update Algorithm (`user_state.py`, lines 838–865)

**Bayesian-style learning:**

```
For each signal in feedback:
  • Positive delta (improved) → modest boost (lr * 0.5)
    "Energy improved" means protocols are working; maintain them
  
  • Negative delta (worsened) → stronger boost (lr * |delta|)
    "Still tired" means energy protocols need more emphasis
  
  For each affected protocol:
    w_new = clip(w_old + lr_adjusted, min=0.10, max=1.00)
    persisted to disk
```

### Layer 5: Per-User Persistence (`user_state.py`, lines 814–832)

Each user's learned weights stored as JSON:

```
model/feedback_weights/
├── weights_alice.json      {"energy_protocol": 0.85, "sleep_protocol": 0.95, ...}
├── weights_bob.json        {"stress_protocol": 0.92, "mood_protocol": 0.80, ...}
└── weights_charlie.json    {...}
```

### Layer 6: Protocol Re-ranking (`user_state.py`, lines 488–530)

Blends baseline + learned weights (70/30 split) to prevent runaway drift:

```python
blended_weight = 0.70 * PROTOCOL_WEIGHTS[proto] + 0.30 * learned_weights[proto]
priority = severity × blended_weight × goal_alignment
```

---

## Integration with Chat Loop

In `model.py` (lines 972–980):

```python
# Extract feedback from user input
feedback = user_state.parse_feedback_from_text(user_input)

if feedback:
    # Update weights based on reported outcomes
    learned_weights = user_state.update_weights_from_feedback(
        user_name, feedback, learning_rate=0.05
    )
    
    # Re-rank protocols using learned weights
    prioritized = user_state.prioritize_protocols(protocols, state, learned_weights)
    print(f"Feedback recorded: {feedback} → Top protocols: [{top_3}]")
```

---

## Usage Examples

### Example 1: Direct Feedback

**User says:** "Energy improved a lot! I'd say energy: +3"

**System extracts:** `{"energy": 3.0}`

**Weight updates:**
- `energy_protocol`: 0.80 → 0.875 (boost = 0.05 × 0.5 × 3 = 0.075)
- `b_complex_protocol`: 0.65 → 0.7125
- `electrolyte_protocol`: 0.55 → 0.6125

**Effect:** Energy-related protocols rank higher next round.

---

### Example 2: Sentiment-based Feedback

**User says:** "I'm feeling more focused and less tired today"

**System extracts:**
```python
{
    "focus": 1.0,     # "more focused" → positive
    "energy": 1.0,    # "less tired" → positive
}
```

**Weight updates:**
- `cognitive_protocol`: 0.72 → 0.736
- `energy_protocol`: 0.80 → 0.8125

---

### Example 3: Negative Feedback

**User says:** "Sleep got worse, still very stressed"

**System extracts:**
```python
{
    "sleep": -1.0,    # "sleep worse" → negative
    "stress": -1.0,   # "very stressed" → negative
}
```

**Weight updates:**
- `sleep_protocol`: 0.90 → 0.95 (boost = 0.05 × 1 = 0.05)
- `stress_protocol`: 0.85 → 0.90

**Effect:** System amplifies these protocols more aggressively since they're not working.

---

## API Reference

### `parse_feedback_from_text(text: str) → dict[str, float]`

Extracts feedback signals from natural language.

**Parameters:**
- `text` (str): User message (e.g., "My energy improved a lot")

**Returns:**
- `dict[str, float]`: Signal strength mapping (e.g., `{"energy": 2.0}`)

**Example:**
```python
feedback = parse_feedback_from_text("energy: +2, feel more focused")
# → {"energy": 2.0, "focus": 1.0}
```

---

### `update_weights_from_feedback(user_name: str, feedback: dict[str, float], learning_rate: float = 0.05) → dict[str, float]`

Updates per-user protocol weights based on feedback and persists to disk.

**Parameters:**
- `user_name` (str): User identifier
- `feedback` (dict): Signal strengths (e.g., `{"energy": 2.0, "stress": -1.0}`)
- `learning_rate` (float): Step size per unit of feedback (default 0.05)

**Returns:**
- `dict[str, float]`: Updated weights (also saved to `feedback_weights/weights_{user}.json`)

**Example:**
```python
feedback = {"energy": 2.0}
weights = update_weights_from_feedback("alice", feedback, learning_rate=0.05)
# → {"energy_protocol": 0.8125, "sleep_protocol": 0.9, ...}
# File saved: model/feedback_weights/weights_alice.json
```

---

### `load_feedback_weights(user_name: str) → dict[str, float]`

Loads per-user learned weights; falls back to baseline if new user.

**Parameters:**
- `user_name` (str): User identifier

**Returns:**
- `dict[str, float]`: Per-user weights or baseline `PROTOCOL_WEIGHTS` if first time

**Example:**
```python
weights = load_feedback_weights("alice")
# → {"energy_protocol": 0.8125, "sleep_protocol": 0.9, ...}
```

---

### `prioritize_protocols(active_protocols: dict[str, float], state: dict, learned_weights: Optional[dict] = None) → list[tuple[str, float]]`

Scores and ranks protocols using blended weights + goal alignment.

**Parameters:**
- `active_protocols` (dict): {protocol_name: severity_score}
- `state` (dict): User health state (e.g., `{"energy": 0.5, "goals": ["boost energy"]}`)
- `learned_weights` (dict, optional): Per-user learned weights

**Returns:**
- `list[tuple[str, float]]`: [(protocol_name, score), ...] sorted by priority

**Example:**
```python
active = {"energy_protocol": 0.8, "sleep_protocol": 0.7}
state = {"energy": 0.5, "goals": ["improve energy"]}
learned = {"energy_protocol": 0.8125, "sleep_protocol": 0.9}

ranked = prioritize_protocols(active, state, learned)
# → [("sleep_protocol", 0.385), ("energy_protocol", 0.318), ...]
```

---

## Learning Dynamics

### Positive Feedback (Smaller Boost)

When user reports improvement, it means the current protocols are working. Apply conservative boost to maintain the approach.

```
Boost = learning_rate × 0.5 × signal_strength
Example: lr=0.05, signal=+2 → boost = 0.025 × 2 = 0.05
```

### Negative Feedback (Larger Boost)

When user reports decline, existing protocols aren't sufficient. Apply aggressive boost to increase these protocols' emphasis.

```
Boost = learning_rate × |signal_strength|
Example: lr=0.05, signal=-2 → boost = 0.05 × 2 = 0.10
```

### Weight Clipping

All weights clamped to [0.10, 1.00] to prevent:
- **Runaway growth**: Weights don't exceed 1.0
- **Protocol dropout**: Weights don't fall below 0.10 (all protocols remain active)

---

## Testing

Run the comprehensive test suite:

```bash
python test_feedback_loop.py
```

**Tests:**
1. **Extraction** (7 cases): Verify all pattern types work correctly
2. **Weight Update** (2 cases): Verify Bayesian update algorithm
3. **Re-ranking** (1 case): Verify learned weights affect protocol priority

**Output:**
```
✅ PASS: Extraction  (all 7 patterns extract correctly)
✅ PASS: Weight Update  (Bayesian update algorithm works)
✅ PASS: Re-ranking  (learned weights improve protocol ranking)
✅ ALL TESTS PASSED
```

---

## Configuration

### Feedback Weights Directory

```python
FEEDBACK_WEIGHTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "feedback_weights"
)
```

Auto-created on first use. Location: `model/feedback_weights/`

### Learning Rate

Default: `0.05` (5% step size per unit of feedback)

Tuning:
- **Increase** (0.10+): Faster learning, more sensitive to single feedback events
- **Decrease** (0.01–0.03): Slower learning, more stable long-term modeling

### Signal-to-Protocol Mapping

Edit `FEEDBACK_PROTOCOL_MAP` to change which protocols respond to specific signals:

```python
FEEDBACK_PROTOCOL_MAP["energy"] = [
    "energy_protocol",
    "b_complex_protocol",
    "electrolyte_protocol",
]
```

---

## Future Enhancements

1. **Contextual Learning**: Weight feedback by time-of-day, recent interventions
2. **Multi-signal Inference**: Infer energy from other signals (sleep quality, mood)
3. **Deprecation**: Phase out protocols that consistently worsen outcomes
4. **Confidence Scoring**: Track uncertainty in learned weights; reset on conflicting feedback
5. **A/B Testing**: Randomize protocol order to test causality vs. correlation

---

## See Also

- [HealthOS Architecture](../README.md)
- [Constraint Graph](./docs/constraint_graph.md)
- [Meal Swap Engine](./docs/meal_swap.md)
- [Trend Analysis](./docs/trend_engine.md)
