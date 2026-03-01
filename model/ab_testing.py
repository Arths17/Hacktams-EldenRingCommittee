"""
A/B Testing Framework for HealthOS.
Run controlled experiments on diet approaches, UI changes, and recommendations.
"""

import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
from scipy import stats as scipy_stats

logger = logging.getLogger(__name__)


class ExperimentStatus(str, Enum):
    """Experiment lifecycle status."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Variant:
    """Experiment variant (control or treatment)."""
    
    def __init__(self, name: str, description: str = "", percentage: float = 50.0):
        """Initialize variant.
        
        Args:
            name: Variant name (e.g., 'control', 'treatment_v1')
            description: Variant description
            percentage: Traffic allocation percentage
        """
        self.name = name
        self.description = description
        self.percentage = percentage
        self.metrics: Dict[str, List[float]] = {}
    
    def record_metric(self, metric_name: str, value: float):
        """Record a metric value for this variant.
        
        Args:
            metric_name: Name of metric
            value: Metric value
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)


class Experiment:
    """A/B test experiment."""
    
    def __init__(self, experiment_id: str, name: str, description: str = "",
                 primary_metric: str = "conversion_rate", start_date: Optional[datetime] = None):
        """Initialize experiment.
        
        Args:
            experiment_id: Unique experiment identifier
            name: Experiment name
            description: What is being tested
            primary_metric: Main metric to optimize
            start_date: When experiment starts
        """
        self.experiment_id = experiment_id
        self.name = name
        self.description = description
        self.primary_metric = primary_metric
        self.status = ExperimentStatus.DRAFT
        self.start_date = start_date or datetime.utcnow()
        self.end_date: Optional[datetime] = None
        self.variants: Dict[str, Variant] = {}
        self.user_assignments: Dict[str, str] = {}  # user_id -> variant_name
    
    def add_variant(self, variant: Variant):
        """Add variant to experiment.
        
        Args:
            variant: Variant instance
        """
        self.variants[variant.name] = variant
    
    def assign_variant(self, user_id: str, force_variant: Optional[str] = None) -> str:
        """Assign user to a variant.
        
        Uses consistent hashing to ensure same user gets same variant across sessions.
        
        Args:
            user_id: User identifier
            force_variant: Force assignment to specific variant (for testing)
            
        Returns:
            Assigned variant name
        """
        if user_id in self.user_assignments:
            return self.user_assignments[user_id]
        
        if force_variant:
            assigned = force_variant
        else:
            # Consistent hashing: same user always gets same variant
            hash_input = f"{self.experiment_id}:{user_id}".encode()
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
            
            # Allocate based on percentages
            cumulative = 0
            assigned = None
            for variant_name, variant in self.variants.items():
                cumulative += variant.percentage
                if (hash_value % 100) < cumulative:
                    assigned = variant_name
                    break
            
            assigned = assigned or list(self.variants.keys())[0]
        
        self.user_assignments[user_id] = assigned
        return assigned
    
    def record_metric(self, user_id: str, metric_value: float):
        """Record primary metric for user.
        
        Args:
            user_id: User identifier
            metric_value: Metric value
        """
        variant = self.user_assignments.get(user_id)
        if variant and variant in self.variants:
            self.variants[variant].record_metric(self.primary_metric, metric_value)
    
    def get_results(self) -> Dict[str, Any]:
        """Get statistical analysis of experiment results.
        
        Returns:
            Results dict with means, confidence intervals, p-values
        """
        results = {
            "experiment_id": self.experiment_id,
            "status": self.status.value,
            "variants": {},
        }
        
        variant_metrics = {}
        for variant_name, variant in self.variants.items():
            metric_values = variant.metrics.get(self.primary_metric, [])
            
            if metric_values:
                mean = statistics.mean(metric_values)
                std_dev = statistics.stdev(metric_values) if len(metric_values) > 1 else 0
                variant_metrics[variant_name] = {
                    "count": len(metric_values),
                    "mean": round(mean, 4),
                    "std_dev": round(std_dev, 4),
                    "metric_values": metric_values,
                }
                
                results["variants"][variant_name] = {
                    "sample_size": len(metric_values),
                    "mean": round(mean, 4),
                    "std_dev": round(std_dev, 4),
                }
            else:
                results["variants"][variant_name] = {"sample_size": 0, "error": "No data"}
        
        # Statistical significance test (t-test if 2+ variants)
        if len(variant_metrics) >= 2:
            variant_names = list(variant_metrics.keys())
            metric1 = variant_metrics[variant_names[0]]["metric_values"]
            metric2 = variant_metrics[variant_names[1]]["metric_values"]
            
            if metric1 and metric2:
                t_stat, p_value = scipy_stats.ttest_ind(metric1, metric2)
                results["statistical_test"] = {
                    "type": "t-test",
                    "t_statistic": round(t_stat, 4),
                    "p_value": round(p_value, 4),
                    "significant_at_0_05": p_value < 0.05,
                    "winner": variant_names[0] if metric1[0] > metric2[0] else variant_names[1],
                }
        
        return results


class ExperimentManager:
    """Manage multiple experiments."""
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
    
    def create_experiment(self, experiment_id: str, name: str, 
                         description: str = "", primary_metric: str = "conversion_rate") -> Experiment:
        """Create new experiment.
        
        Args:
            experiment_id: Unique identifier
            name: Experiment name
            description: What is being tested
            primary_metric: Metric to optimize
            
        Returns:
            Created experiment
        """
        exp = Experiment(experiment_id, name, description, primary_metric)
        self.experiments[experiment_id] = exp
        logger.info(f"✓ Experiment created: {name} ({experiment_id})")
        return exp
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        return self.experiments.get(experiment_id)
    
    def start_experiment(self, experiment_id: str):
        """Start running experiment.
        
        Args:
            experiment_id: Experiment identifier
        """
        exp = self.get_experiment(experiment_id)
        if exp:
            exp.status = ExperimentStatus.RUNNING
            logger.info(f"✓ Experiment started: {experiment_id}")
    
    def end_experiment(self, experiment_id: str):
        """End experiment and mark complete.
        
        Args:
            experiment_id: Experiment identifier
        """
        exp = self.get_experiment(experiment_id)
        if exp:
            exp.status = ExperimentStatus.COMPLETED
            exp.end_date = datetime.utcnow()
            logger.info(f"✓ Experiment completed: {experiment_id}")
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """Get results for all experiments.
        
        Returns:
            List of experiment results
        """
        return [exp.get_results() for exp in self.experiments.values()]


# Example usage helper
def create_meal_diet_experiment(manager: ExperimentManager) -> Experiment:
    """Create an A/B test for different diet approaches.
    
    Args:
        manager: ExperimentManager instance
        
    Returns:
        Created experiment
    """
    exp = manager.create_experiment(
        "diet_approach_ab_001",
        "Low-carb vs Balanced Diet",
        "Testing whether low-carb approach increases adherence vs balanced diet",
        primary_metric="meal_adherence_rate"
    )
    
    control = Variant("control_balanced", "Standard balanced diet recommendations")
    control.percentage = 50.0
    
    treatment = Variant("treatment_lowcarb", "Low-carb diet recommendations")
    treatment.percentage = 50.0
    
    exp.add_variant(control)
    exp.add_variant(treatment)
    
    return exp


# Global instance
experiment_manager = ExperimentManager()
