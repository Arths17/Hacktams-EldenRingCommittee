"""
Churn Model Training Script for HealthOS AI

Generates synthetic user engagement data, trains the churn prediction model,
and saves trained weights for production use.

Run: python train_churn_model.py
"""

import os
import json
import numpy as np
import pickle
from datetime import datetime, timedelta
from typing import Tuple, Dict, List
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

print("=" * 70)
print("  HealthOS AI - Churn Model Training Pipeline")
print("=" * 70)
print()


# ============================================================================
# STEP 1: GENERATE SYNTHETIC USER ENGAGEMENT DATA
# ============================================================================

def generate_user_engagement_data(n_users: int = 500, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic user engagement data for model training.
    
    Args:
        n_users: Number of synthetic users to generate
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (features, labels)
    """
    np.random.seed(seed)
    
    print("📍 Step 1: Generating synthetic user engagement data")
    print(f"   Generating data for {n_users} users...")
    
    features = []
    labels = []
    
    for _ in range(n_users):
        # Feature 1: Days since last login (0-60)
        days_since_login = np.random.randint(0, 60)
        
        # Feature 2: Login frequency (0-20 per week)
        login_freq = np.random.uniform(0, 20)
        
        # Feature 3: Goals completion rate (0-1)
        goal_completion = np.random.uniform(0, 1)
        
        # Feature 4: Meal adherence rate (0-1)
        meal_adherence = np.random.uniform(0, 1)
        
        # Feature 5: Feedback frequency (0-10 per week)
        feedback_freq = np.random.uniform(0, 10)
        
        # Feature 6: Activity consistency (0-1)
        activity_consistency = np.random.uniform(0, 1)
        
        # Feature 7: Profile completion (0-100%)
        profile_completion = np.random.uniform(0, 100)
        
        # Feature 8: Health check frequency (0-10 per week)
        health_freq = np.random.uniform(0, 10)
        
        feature_vector = np.array([
            days_since_login,
            login_freq,
            goal_completion,
            meal_adherence,
            feedback_freq,
            activity_consistency,
            profile_completion / 100,  # Normalize
            health_freq,
        ])
        
        # Generate label based on risk factors
        # Higher risk factors increase churn probability
        risk_score = (
            (days_since_login / 60) * 0.25 +
            (1 - login_freq / 20) * 0.15 +
            (1 - goal_completion) * 0.20 +
            (1 - meal_adherence) * 0.15 +
            (1 - feedback_freq / 10) * 0.10 +
            (1 - activity_consistency) * 0.10 +
            (1 - profile_completion / 100) * 0.05
        )
        
        # Add noise
        risk_score += np.random.normal(0, 0.1)
        risk_score = np.clip(risk_score, 0, 1)
        
        # Label: 1 if likely to churn (risk > threshold), 0 otherwise
        churn_label = 1 if risk_score > 0.5 else 0
        
        features.append(feature_vector)
        labels.append(churn_label)
    
    X = np.array(features)
    y = np.array(labels)
    
    print(f"✓ Generated {n_users} users")
    print(f"  - Churn cases: {np.sum(y)} ({np.sum(y)/len(y)*100:.1f}%)")
    print(f"  - Active cases: {len(y) - np.sum(y)} ({(1-np.sum(y)/len(y))*100:.1f}%)")
    print()
    
    return X, y


# ============================================================================
# STEP 2: SPLIT DATA
# ============================================================================

def split_data(X: np.ndarray, y: np.ndarray, test_size: float = 0.2) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split data into training and testing sets."""
    print("📍 Step 2: Splitting data")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    print(f"✓ Training set: {len(X_train)} samples ({len(X_train)/len(X)*100:.1f}%)")
    print(f"✓ Testing set: {len(X_test)} samples ({len(X_test)/len(X)*100:.1f}%)")
    print()
    
    return X_train, X_test, y_train, y_test


# ============================================================================
# STEP 3: SCALE FEATURES
# ============================================================================

def scale_features(X_train: np.ndarray, X_test: np.ndarray) -> Tuple[np.ndarray, np.ndarray, StandardScaler]:
    """Scale features using StandardScaler."""
    print("📍 Step 3: Scaling features")
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print(f"✓ Features scaled")
    print(f"  - Mean: {X_train_scaled.mean(axis=0).mean():.4f}")
    print(f"  - Std: {X_train_scaled.std(axis=0).mean():.4f}")
    print()
    
    return X_train_scaled, X_test_scaled, scaler


# ============================================================================
# STEP 4: TRAIN MODEL
# ============================================================================

def train_model(X_train: np.ndarray, y_train: np.ndarray) -> LogisticRegression:
    """Train logistic regression model."""
    print("📍 Step 4: Training logistic regression model")
    
    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        solver='lbfgs',
        class_weight='balanced',  # Handle imbalanced classes
    )
    
    model.fit(X_train, y_train)
    
    print(f"✓ Model trained")
    print(f"  - Converged: {model.n_iter_[0]} iterations")
    print()
    
    return model


# ============================================================================
# STEP 5: EVALUATE MODEL
# ============================================================================

def evaluate_model(
    model: LogisticRegression,
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    feature_names: List[str]
) -> Dict:
    """Evaluate model performance on both sets."""
    print("📍 Step 5: Evaluating model performance")
    print()
    
    # Training metrics
    train_pred = model.predict(X_train)
    train_proba = model.predict_proba(X_train)[:, 1]
    
    train_acc = accuracy_score(y_train, train_pred)
    train_prec = precision_score(y_train, train_pred)
    train_rec = recall_score(y_train, train_pred)
    train_f1 = f1_score(y_train, train_pred)
    train_auc = roc_auc_score(y_train, train_proba)
    
    print("Training Set Metrics:")
    print(f"  - Accuracy: {train_acc:.4f}")
    print(f"  - Precision: {train_prec:.4f}")
    print(f"  - Recall: {train_rec:.4f}")
    print(f"  - F1-Score: {train_f1:.4f}")
    print(f"  - AUC-ROC: {train_auc:.4f}")
    print()
    
    # Testing metrics
    test_pred = model.predict(X_test)
    test_proba = model.predict_proba(X_test)[:, 1]
    
    test_acc = accuracy_score(y_test, test_pred)
    test_prec = precision_score(y_test, test_pred)
    test_rec = recall_score(y_test, test_pred)
    test_f1 = f1_score(y_test, test_pred)
    test_auc = roc_auc_score(y_test, test_proba)
    
    print("Testing Set Metrics:")
    print(f"  - Accuracy: {test_acc:.4f}")
    print(f"  - Precision: {test_prec:.4f}")
    print(f"  - Recall: {test_rec:.4f}")
    print(f"  - F1-Score: {test_f1:.4f}")
    print(f"  - AUC-ROC: {test_auc:.4f}")
    print()
    
    # Confusion matrix
    cm = confusion_matrix(y_test, test_pred)
    print("Confusion Matrix:")
    print(f"  True Negatives: {cm[0, 0]}")
    print(f"  False Positives: {cm[0, 1]}")
    print(f"  False Negatives: {cm[1, 0]}")
    print(f"  True Positives: {cm[1, 1]}")
    print()
    
    # Feature importance
    print("Feature Importance (Coefficients):")
    for name, coef in zip(feature_names, model.coef_[0]):
        direction = "↑" if coef > 0 else "↓"
        print(f"  {direction} {name:30s}: {coef:7.4f}")
    print()
    
    metrics = {
        "train_accuracy": float(train_acc),
        "train_precision": float(train_prec),
        "train_recall": float(train_rec),
        "train_f1": float(train_f1),
        "train_auc": float(train_auc),
        "test_accuracy": float(test_acc),
        "test_precision": float(test_prec),
        "test_recall": float(test_rec),
        "test_f1": float(test_f1),
        "test_auc": float(test_auc),
        "confusion_matrix": cm.tolist(),
    }
    
    return metrics


# ============================================================================
# STEP 6: SAVE MODEL
# ============================================================================

def save_model(
    model: LogisticRegression,
    scaler: StandardScaler,
    feature_names: List[str],
    metrics: Dict,
) -> str:
    """Save trained model and scaler to files."""
    print("📍 Step 6: Saving model artifacts")
    
    # Create models directory
    os.makedirs("model/trained_models", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save model
    model_path = f"model/trained_models/churn_model_{timestamp}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"✓ Model saved: {model_path}")
    
    # Save scaler
    scaler_path = f"model/trained_models/churn_scaler_{timestamp}.pkl"
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"✓ Scaler saved: {scaler_path}")
    
    # Save metrics
    metrics_path = f"model/trained_models/churn_metrics_{timestamp}.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Metrics saved: {metrics_path}")
    
    # Save model info
    model_info = {
        "timestamp": timestamp,
        "features": feature_names,
        "model_type": "LogisticRegression",
        "intercept": float(model.intercept_[0]),
        "coefficients": model.coef_[0].tolist(),
        "metrics": metrics,
        "created_at": datetime.now().isoformat(),
    }
    
    info_path = f"model/trained_models/churn_model_info_{timestamp}.json"
    with open(info_path, "w") as f:
        json.dump(model_info, f, indent=2)
    print(f"✓ Model info saved: {info_path}")
    
    # Create symlinks to latest versions
    latest_model_path = "model/trained_models/churn_model_latest.pkl"
    latest_scaler_path = "model/trained_models/churn_scaler_latest.pkl"
    latest_metrics_path = "model/trained_models/churn_metrics_latest.json"
    latest_info_path = "model/trained_models/churn_model_info_latest.json"
    
    # Remove old symlinks
    for path in [latest_model_path, latest_scaler_path, latest_metrics_path, latest_info_path]:
        if os.path.islink(path):
            os.remove(path)
    
    # Create new symlinks
    os.symlink(os.path.basename(model_path), latest_model_path)
    os.symlink(os.path.basename(scaler_path), latest_scaler_path)
    os.symlink(os.path.basename(metrics_path), latest_metrics_path)
    os.symlink(os.path.basename(info_path), latest_info_path)
    
    print(f"✓ Latest symlinks created")
    print()
    
    return timestamp


# ============================================================================
# STEP 7: INTEGRATION WITH PRODUCTION MODEL
# ============================================================================

def update_production_model(model: LogisticRegression, scaler: StandardScaler, timestamp: str):
    """Update the production churn_prediction.py with new model weights."""
    print("📍 Step 7: Updating production model")
    
    # Save weights to JSON for inspection
    weights_info = {
        "timestamp": timestamp,
        "model_type": "LogisticRegression",
        "intercept": float(model.intercept_[0]),
        "coefficients": model.coef_[0].tolist(),
        "classes": model.classes_.tolist(),
    }
    
    weights_path = f"model/trained_models/weights_{timestamp}.json"
    with open(weights_path, "w") as f:
        json.dump(weights_info, f, indent=2)
    
    print(f"✓ Model weights exported: {weights_path}")
    print()
    print("To update production model:")
    print("1. Load model/trained_models/churn_model_latest.pkl in your code")
    print("2. Or copy coefficients to model/churn_prediction.py _init_default_model()")
    print()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        # Feature names
        feature_names = [
            "days_since_last_login",
            "login_frequency",
            "goals_completion_rate",
            "meal_adherence_rate",
            "feedback_frequency",
            "activity_consistency",
            "profile_completion",
            "health_check_frequency",
        ]
        
        # Step 1: Generate data
        X, y = generate_user_engagement_data(n_users=500)
        
        # Step 2: Split data
        X_train, X_test, y_train, y_test = split_data(X, y)
        
        # Step 3: Scale features
        X_train_scaled, X_test_scaled, scaler = scale_features(X_train, X_test)
        
        # Step 4: Train model
        model = train_model(X_train_scaled, y_train)
        
        # Step 5: Evaluate model
        metrics = evaluate_model(
            model, X_train_scaled, X_test_scaled, y_train, y_test, feature_names
        )
        
        # Step 6: Save model
        timestamp = save_model(model, scaler, feature_names, metrics)
        
        # Step 7: Update production
        update_production_model(model, scaler, timestamp)
        
        print("=" * 70)
        print("  ✅ TRAINING COMPLETE")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  Test AUC-ROC: {metrics['test_auc']:.4f}")
        print(f"  Test F1-Score: {metrics['test_f1']:.4f}")
        print(f"  Model saved with timestamp: {timestamp}")
        print()
        print("Next steps:")
        print("  1. Review model_info_latest.json for detailed metrics")
        print("  2. Deploy model to production")
        print("  3. Monitor prediction accuracy in production")
        print()
        
    except Exception as e:
        print(f"❌ Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
