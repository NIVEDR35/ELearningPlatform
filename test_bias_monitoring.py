#!/usr/bin/env python3
"""Test Bias Monitoring System"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from bias_monitor import BiasMonitor

print("=" * 80)
print("🔍 TESTING BIAS MONITORING SYSTEM")
print("=" * 80)

with app.app_context():
    monitor = BiasMonitor()
    
    # Run comprehensive bias analysis
    print("\n📊 Running bias analysis...\n")
    analysis = monitor.analyze_recommendation_bias()
    
    # Generate and print report
    report = monitor.generate_bias_report()
    print(report)
    
    # Get mitigation strategies
    print("\n💡 MITIGATION STRATEGIES")
    print("=" * 80)
    strategies = monitor.get_mitigation_strategies(analysis)
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy}")
    
    print("\n" + "=" * 80)
    print("✅ BIAS MONITORING SYSTEM IS OPERATIONAL!")
    print("=" * 80)
