#!/usr/bin/env python3
"""
API Performance Testing — Load testing and benchmarking for HealthOS API.
"""

import time
import asyncio
import json
from typing import List, Tuple
import statistics

try:
    import requests
    import httpx
except ImportError:
    print("Install: pip install requests httpx")
    exit(1)


class APIBenchmark:
    """Benchmark HealthOS API performance."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: dict = {"endpoints": {}}
    
    def benchmark_endpoint(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
        headers: dict = None,
        iterations: int = 10,
        name: str = None,
    ) -> dict:
        """Benchmark a single endpoint."""
        name = name or f"{method} {endpoint}"
        times: List[float] = []
        errors = 0
        
        print(f"\n📊 Benchmarking: {name} ({iterations} iterations)")
        
        for i in range(iterations):
            start = time.time()
            try:
                if method == "GET":
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        timeout=10,
                    )
                elif method == "POST":
                    response = requests.post(
                        f"{self.base_url}{endpoint}",
                        json=data,
                        headers=headers,
                        timeout=10,
                    )
                else:
                    raise ValueError(f"Unknown method: {method}")
                
                elapsed = time.time() - start
                times.append(elapsed * 1000)  # Convert to ms
                
                status = "✓" if response.status_code < 400 else "✗"
                print(f"  {i+1:2d}. {status} {response.status_code} in {elapsed*1000:.1f}ms")
            
            except Exception as e:
                elapsed = time.time() - start
                times.append(elapsed * 1000)
                errors += 1
                print(f"  {i+1:2d}. ✗ Error: {e}")
        
        # Calculate statistics
        stats = {
            "name": name,
            "iterations": iterations,
            "errors": errors,
            "success_rate": ((iterations - errors) / iterations) * 100,
            "min_ms": min(times),
            "max_ms": max(times),
            "avg_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "p95_ms": sorted(times)[int(0.95 * len(times))],
            "p99_ms": sorted(times)[int(0.99 * len(times))],
        }
        
        self.results["endpoints"][name] = stats
        
        # Print summary
        print(f"\n  📈 Summary:")
        print(f"    Avg: {stats['avg_ms']:.1f}ms | Median: {stats['median_ms']:.1f}ms | StDev: {stats['stdev_ms']:.1f}ms")
        print(f"    p95: {stats['p95_ms']:.1f}ms | p99: {stats['p99_ms']:.1f}ms")
        print(f"    Success: {stats['success_rate']:.1f}% ({iterations - errors}/{iterations})")
        
        return stats
    
    def benchmark_health_check(self, iterations: int = 10):
        """Benchmark GET /api/health."""
        return self.benchmark_endpoint("GET", "/api/health", iterations=iterations, name="Health Check")
    
    def benchmark_login(self, iterations: int = 5):
        """Benchmark POST /login."""
        return self.benchmark_endpoint(
            "POST",
            "/login",
            data={"username": "testuser", "password": "testpass123"},
            iterations=iterations,
            name="Login (form data)",
        )
    
    def benchmark_profile_get(self, token: str, iterations: int = 10):
        """Benchmark GET /api/me."""
        headers = {"Authorization": f"Bearer {token}"}
        return self.benchmark_endpoint(
            "GET",
            "/api/me",
            headers=headers,
            iterations=iterations,
            name="Get Profile",
        )
    
    def benchmark_profile_update(self, token: str, iterations: int = 5):
        """Benchmark POST /api/profile."""
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "age": 20,
            "weight_kg": 75.0,
            "activity_level": "moderate",
            "health_goals": ["improve energy"],
        }
        return self.benchmark_endpoint(
            "POST",
            "/api/profile",
            data=data,
            headers=headers,
            iterations=iterations,
            name="Update Profile",
        )
    
    def benchmark_rate_limiting(self):
        """Test rate limiting behavior."""
        print(f"\n🔒 Testing Rate Limiting")
        endpoint = "/login"
        limit = 5
        window = 300
        
        times = []
        for i in range(limit + 3):
            start = time.time()
            try:
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    data={"username": "test", "password": "test123"},
                    timeout=5,
                )
                elapsed = time.time() - start
                times.append(elapsed)
                
                if response.status_code == 429:
                    print(f"  {i+1}. ✓ Rate limit triggered: {response.json()}")
                    break
                else:
                    print(f"  {i+1}. ✓ {response.status_code} in {elapsed*1000:.1f}ms")
            
            except Exception as e:
                print(f"  {i+1}. ✗ Error: {e}")
    
    def print_report(self):
        """Print benchmark report."""
        print("\n" + "="*70)
        print("  HealthOS API Performance Report")
        print("="*70)
        
        print(f"\n📊 Endpoint Benchmarks:\n")
        print(f"{'Endpoint':<30} {'Avg':<10} {'p95':<10} {'p99':<10} {'Success':<10}")
        print("-" * 70)
        
        for name, stats in self.results["endpoints"].items():
            print(
                f"{name:<30} "
                f"{stats['avg_ms']:<9.1f}ms "
                f"{stats['p95_ms']:<9.1f}ms "
                f"{stats['p99_ms']:<9.1f}ms "
                f"{stats['success_rate']:<9.1f}%"
            )
        
        # Calculate total metrics
        all_times = []
        total_errors = 0
        total_requests = 0
        
        for stats in self.results["endpoints"].values():
            total_requests += stats["iterations"]
            total_errors += stats["errors"]
        
        print("-" * 70)
        print(f"{'TOTAL':<30} {total_requests:<10} {total_errors:<10} errors")
        print("="*70 + "\n")
    
    def save_report(self, filename: str = "benchmark_results.json"):
        """Save results to JSON file."""
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"✓ Report saved to {filename}")


def main():
    """Run comprehensive API benchmarks."""
    benchmark = APIBenchmark(base_url="http://localhost:8000")
    
    print("\n" + "="*70)
    print("  HealthOS API — Performance Benchmark Suite")
    print("="*70)
    print("\n🔍 Testing endpoint performance and rate limiting...\n")
    
    # Health checks
    benchmark.benchmark_health_check(iterations=10)
    
    # Login attempts (to get a token for authenticated endpoints)
    login_result = benchmark.benchmark_login(iterations=3)
    
    # Extract token if login succeeded
    token = None
    if login_result["success_rate"] > 0:
        try:
            response = requests.post(
                "http://localhost:8000/login",
                data={"username": "testuser", "password": "testpass123"},
            )
            if response.status_code == 200:
                token = response.json().get("token")
        except:
            pass
    
    # Authenticated endpoint benchmarks
    if token:
        benchmark.benchmark_profile_get(token, iterations=10)
        benchmark.benchmark_profile_update(token, iterations=5)
    else:
        print("\n⚠️  Skipping authenticated endpoint benchmarks (login failed)")
    
    # Rate limiting test
    benchmark.benchmark_rate_limiting()
    
    # Print report
    benchmark.print_report()
    benchmark.save_report()


if __name__ == "__main__":
    main()
