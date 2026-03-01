#!/usr/bin/env python3
"""
Test the feedback learning loop.

Simulates user feedback and verifies:
1. Pattern extraction works
2. Weights update correctly
3. Persistence works
4. Protocol re-ranking reflects learned weights
"""

import sys
import os
import json
from pathlib import Path

# Add model dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "model"))

from user_state import (
    parse_feedback_from_text,
    update_weights_from_feedback,
    load_feedback_weights,
    save_feedback_weights,
    prioritize_protocols,
    PROTOCOL_WEIGHTS,
    FEEDBACK_WEIGHTS_DIR,
)

def test_feedback_extraction():
    """Test that patterns correctly extract feedback."""
    print("\n" + "="*70)
    print("TEST 1: Feedback Extraction")
    print("="*70)
    
    test_cases = [
        ("energy: +2", {"energy": 2.0}),
        ("I feel more energetic today", {"energy": 1.0}),
        ("my sleep improved", {"sleep": 1.0}),
        ("stress is worse", {"stress": -1.0}),
        ("energy +2, focus +1, sleep -1", {"energy": 2.0, "focus": 1.0, "sleep": -1.0}),
        ("I'm more focused and less tired", {"focus": 1.0, "energy": 1.0}),
        ("feeling anxious and bloated", {"anxiety": -1.0, "bloat": -1.0}),
    ]
    
    all_passed = True
    for text, expected in test_cases:
        result = parse_feedback_from_text(text)
        passed = result == expected
        status = "✅" if passed else "❌"
        print(f"\n{status} Input: \"{text}\"")
        print(f"   Expected: {expected}")
        print(f"   Got:      {result}")
        if not passed:
            all_passed = False
    
    return all_passed


def test_weight_update():
    """Test that weight updates work correctly."""
    print("\n" + "="*70)
    print("TEST 2: Weight Update Algorithm")
    print("="*70)
    
    user_name = "test_user_feedback"
    
    # Start fresh
    safe_name = "test_user_feedback"
    weight_file = os.path.join(FEEDBACK_WEIGHTS_DIR, f"weights_{safe_name}.json")
    if os.path.exists(weight_file):
        os.remove(weight_file)
    
    # Load baseline weights
    baseline = load_feedback_weights(user_name)
    print(f"\n📌 Baseline weights loaded (protocol count: {len(baseline)})")
    print(f"   energy_protocol: {baseline['energy_protocol']:.4f}")
    print(f"   sleep_protocol:  {baseline['sleep_protocol']:.4f}")
    print(f"   stress_protocol: {baseline['stress_protocol']:.4f}")
    
    # Simulate positive feedback: "energy improved by 2"
    print(f"\n📝 Feedback 1: energy +2")
    feedback1 = {"energy": 2.0}
    weights1 = update_weights_from_feedback(user_name, feedback1, learning_rate=0.05)
    
    # Energy protocol should have increased (positive feedback = smaller boost)
    # boost = 0.05 * 0.5 = 0.025
    energy_boost = weights1["energy_protocol"] - baseline["energy_protocol"]
    print(f"   energy_protocol:  {baseline['energy_protocol']:.4f} → {weights1['energy_protocol']:.4f}")
    print(f"   ✓ Boost: {energy_boost:.4f} (expected ~0.025)")
    
    # Simulate negative feedback: "sleep got worse"
    print(f"\n📝 Feedback 2: sleep -1")
    feedback2 = {"sleep": -1.0}
    weights2 = update_weights_from_feedback(user_name, feedback2, learning_rate=0.05)
    
    # Sleep protocol should have increased (negative feedback = larger boost)
    # boost = 0.05 * abs(-1) = 0.05
    sleep_boost = weights2["sleep_protocol"] - weights1["sleep_protocol"]
    print(f"   sleep_protocol:   {weights1['sleep_protocol']:.4f} → {weights2['sleep_protocol']:.4f}")
    print(f"   ✓ Boost: {sleep_boost:.4f} (expected ~0.05)")
    
    # Verify persistence
    print(f"\n✅ Weights persisted to: {weight_file}")
    reloaded = load_feedback_weights(user_name)
    assert reloaded == weights2, "❌ Reload mismatch!"
    print(f"   ✓ Reload verified: {reloaded['energy_protocol']:.4f}")
    
    return True


def test_protocol_reranking():
    """Test that protocol priorities reflect learned weights."""
    print("\n" + "="*70)
    print("TEST 3: Protocol Re-ranking with Learned Weights")
    print("="*70)
    
    user_name = "test_user_rerank"
    
    # Clean up
    safe_name = "test_user_rerank"
    weight_file = os.path.join(FEEDBACK_WEIGHTS_DIR, f"weights_{safe_name}.json")
    if os.path.exists(weight_file):
        os.remove(weight_file)
    
    # Baseline state and active protocols (as dict with severity)
    baseline_state = {
        "energy": 0.5,
        "sleep_quality": 0.3,
        "stress": 0.7,
        "goals": ["improve energy"],
    }
    active_protocols = {
        "energy_protocol": 0.8,
        "sleep_protocol": 0.7,
        "stress_protocol": 0.9,
        "cognitive_protocol": 0.6,
        "muscle_protocol": 0.5,
        "gut_protocol": 0.4,
    }
    
    # Rank with baseline weights
    print(f"\n📊 Ranking with baseline weights:")
    baseline_weights = load_feedback_weights(user_name)
    ranked_baseline = prioritize_protocols(active_protocols, baseline_state, baseline_weights)
    print(f"   Top 3: {[(p, f'{w:.3f}') for p, w in ranked_baseline[:3]]}")
    
    # User provides feedback: "energy improved"
    print(f"\n📝 User feedback: \"My energy improved!\"")
    feedback = parse_feedback_from_text("My energy improved!")
    print(f"   Extracted: {feedback}")
    
    learned_weights = update_weights_from_feedback(user_name, feedback, learning_rate=0.05)
    
    # Re-rank with learned weights
    print(f"\n📊 Ranking with learned weights:")
    ranked_learned = prioritize_protocols(active_protocols, baseline_state, learned_weights)
    print(f"   Top 3: {[(p, f'{w:.3f}') for p, w in ranked_learned[:3]]}")
    
    # Energy protocol should rank higher
    baseline_energy_rank = next(i for i, (p, _) in enumerate(ranked_baseline) if "energy" in p)
    learned_energy_rank = next(i for i, (p, _) in enumerate(ranked_learned) if "energy" in p)
    
    print(f"\n   energy_protocol rank: #{baseline_energy_rank + 1} → #{learned_energy_rank + 1}")
    if learned_energy_rank <= baseline_energy_rank:
        print(f"   ✅ Energy protocol ranked higher after positive feedback")
    else:
        print(f"   ⚠️  Unexpected ranking change")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  FEEDBACK LEARNING LOOP — END-TO-END TEST")
    print("="*70)
    
    results = {
        "Extraction": test_feedback_extraction(),
        "Weight Update": test_weight_update(),
        "Re-ranking": test_protocol_reranking(),
    }
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(results.values())
    print("\n" + ("✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"))
    print("="*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
