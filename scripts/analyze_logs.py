#!/usr/bin/env python3
"""
Log Analysis Tool

Analyze log files and generate reports:
- Error summary
- Performance metrics
- Request statistics
- Component health

Usage:
    python scripts/analyze_logs.py
    python scripts/analyze_logs.py --today
    python scripts/analyze_logs.py --errors-only
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import argparse


class LogAnalyzer:
    """Analyze log files and generate reports"""
    
    def __init__(self, log_dir='logs'):
        self.log_dir = Path(log_dir)
        self.logs = []
        self.errors = []
        self.warnings = []
        self.requests = []
        self.performance = []
        
    def load_logs(self, filename=None, date_filter=None):
        """Load logs from file(s)"""
        if filename:
            files = [self.log_dir / filename]
        else:
            files = list(self.log_dir.glob('*.log'))
            # Exclude backups
            files = [f for f in files if not re.search(r'\.\d{4}-\d{2}-\d{2}', f.name)]
        
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        log_entry = self.parse_log_line(line)
                        if log_entry:
                            # Date filter
                            if date_filter:
                                log_date = datetime.strptime(log_entry['timestamp'], '%Y-%m-%d %H:%M:%S').date()
                                if log_date != date_filter:
                                    continue
                            
                            self.logs.append(log_entry)
                            
                            # Categorize
                            if log_entry['level'] in ['ERROR', 'CRITICAL']:
                                self.errors.append(log_entry)
                            elif log_entry['level'] == 'WARNING':
                                self.warnings.append(log_entry)
                            
                            # Extract metrics
                            if 'REQUEST' in log_entry['message']:
                                self.requests.append(log_entry)
                            elif 'took' in log_entry['message']:
                                self.performance.append(log_entry)
                                
            except Exception as e:
                print(f"⚠️  Error reading {filepath}: {e}")
    
    def parse_log_line(self, line):
        """Parse log line"""
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (\S+) - (\w+) - (.+)'
        match = re.match(pattern, line)
        
        if match:
            timestamp, component, level, message = match.groups()
            return {
                'timestamp': timestamp,
                'component': component,
                'level': level,
                'message': message.strip()
            }
        return None
    
    def extract_duration(self, message):
        """Extract duration from message (e.g., 'took 1.23s')"""
        match = re.search(r'took ([\d.]+)s', message)
        if match:
            return float(match.group(1))
        return None
    
    def generate_report(self):
        """Generate comprehensive report"""
        print("=" * 80)
        print("📊 RAG System Log Analysis Report")
        print("=" * 80)
        print()
        
        # 1. Overview
        print("📈 OVERVIEW")
        print("-" * 80)
        print(f"Total logs:     {len(self.logs):,}")
        print(f"Errors:         {len(self.errors):,}")
        print(f"Warnings:       {len(self.warnings):,}")
        print(f"Requests:       {len(self.requests):,}")
        print()
        
        # 2. Component breakdown
        print("🔧 COMPONENT BREAKDOWN")
        print("-" * 80)
        component_stats = Counter(log['component'] for log in self.logs)
        for component, count in component_stats.most_common():
            errors = sum(1 for log in self.errors if log['component'] == component)
            error_rate = (errors / count * 100) if count > 0 else 0
            status = "✅" if error_rate == 0 else ("⚠️ " if error_rate < 5 else "❌")
            print(f"{status} {component:30} | Logs: {count:6,} | Errors: {errors:4,} ({error_rate:5.1f}%)")
        print()
        
        # 3. Error analysis
        if self.errors:
            print("❌ ERROR ANALYSIS")
            print("-" * 80)
            print(f"Total errors: {len(self.errors)}")
            print()
            
            # Error messages
            error_messages = Counter(log['message'][:100] for log in self.errors)
            print("Top 10 error messages:")
            for i, (msg, count) in enumerate(error_messages.most_common(10), 1):
                print(f"  {i}. [{count:3}x] {msg}...")
            print()
        
        # 4. Warning analysis
        if self.warnings:
            print("⚠️  WARNING ANALYSIS")
            print("-" * 80)
            print(f"Total warnings: {len(self.warnings)}")
            print()
            
            warning_messages = Counter(log['message'][:80] for log in self.warnings)
            print("Top 5 warning messages:")
            for i, (msg, count) in enumerate(warning_messages.most_common(5), 1):
                print(f"  {i}. [{count:3}x] {msg}...")
            print()
        
        # 5. Performance analysis
        if self.performance:
            print("⚡ PERFORMANCE METRICS")
            print("-" * 80)
            
            durations = []
            for log in self.performance:
                duration = self.extract_duration(log['message'])
                if duration:
                    durations.append(duration)
            
            if durations:
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                min_duration = min(durations)
                
                print(f"Total operations: {len(durations):,}")
                print(f"Average time:     {avg_duration:.2f}s")
                print(f"Min time:         {min_duration:.2f}s")
                print(f"Max time:         {max_duration:.2f}s")
                
                # Slow operations (> 5s)
                slow_ops = [d for d in durations if d > 5.0]
                if slow_ops:
                    print(f"Slow operations:  {len(slow_ops)} (>{5}s)")
            print()
        
        # 6. Request analysis
        if self.requests:
            print("📨 REQUEST STATISTICS")
            print("-" * 80)
            
            # Extract request types
            request_types = Counter()
            for log in self.requests:
                match = re.search(r'REQUEST (\w+) (/\S+)', log['message'])
                if match:
                    method, path = match.groups()
                    request_types[f"{method} {path}"] += 1
            
            print(f"Total requests: {len(self.requests):,}")
            print()
            print("Top endpoints:")
            for endpoint, count in request_types.most_common(10):
                print(f"  {count:4,}x {endpoint}")
            print()
        
        # 7. Timeline
        if self.logs:
            print("📅 TIMELINE")
            print("-" * 80)
            
            times = []
            for log in self.logs:
                try:
                    dt = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')
                    times.append(dt)
                except:
                    pass
            
            if times:
                first_log = min(times)
                last_log = max(times)
                duration = last_log - first_log
                
                print(f"First log: {first_log.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Last log:  {last_log.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Duration:  {duration}")
                
                # Hourly distribution
                hour_dist = Counter(t.hour for t in times)
                print()
                print("Activity by hour:")
                for hour in sorted(hour_dist.keys()):
                    count = hour_dist[hour]
                    bar = '█' * (count // (max(hour_dist.values()) // 40 + 1))
                    print(f"  {hour:02d}:00 | {bar} {count:,}")
            print()
        
        print("=" * 80)
        print("✅ Analysis complete")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Analyze RAG system logs')
    parser.add_argument('--file', type=str, help='Specific log file to analyze')
    parser.add_argument('--today', action='store_true', help='Analyze only today\'s logs')
    parser.add_argument('--errors-only', action='store_true', help='Show only errors')
    
    args = parser.parse_args()
    
    analyzer = LogAnalyzer()
    
    # Date filter
    date_filter = datetime.now().date() if args.today else None
    
    print()
    print("📂 Loading logs...")
    analyzer.load_logs(filename=args.file, date_filter=date_filter)
    
    if not analyzer.logs:
        print("❌ No logs found")
        return
    
    print(f"✅ Loaded {len(analyzer.logs):,} log entries")
    print()
    
    if args.errors_only:
        if analyzer.errors:
            print("❌ ERRORS FOUND:")
            print("=" * 80)
            for error in analyzer.errors[-20:]:  # Last 20 errors
                print(f"{error['timestamp']} | {error['component']} | {error['message']}")
        else:
            print("✅ No errors found!")
    else:
        analyzer.generate_report()
    
    print()


if __name__ == '__main__':
    main()
