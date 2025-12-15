#!/usr/bin/env python3
"""
Real-time Log Monitoring Dashboard

Monitor logs from all components:
- MCP Server
- Document Processor
- Web Interface
- RAG Service

Usage:
    python scripts/monitor_logs.py
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque
import re

# ANSI colors
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Log level colors
LEVEL_COLORS = {
    'DEBUG': '\033[36m',    # Cyan
    'INFO': '\033[32m',     # Green
    'WARNING': '\033[33m',  # Yellow
    'ERROR': '\033[31m',    # Red
    'CRITICAL': '\033[35m', # Magenta
}

# Component colors
COMPONENT_COLORS = {
    'mcp_server': '\033[94m',      # Light Blue
    'document_processor': '\033[92m',  # Light Green
    'app': '\033[95m',             # Light Magenta
    'rag_service': '\033[93m',     # Light Yellow
}


class LogMonitor:
    """Real-time log file monitor"""
    
    def __init__(self, log_dir='logs'):
        self.log_dir = Path(log_dir)
        self.files = {}
        self.stats = defaultdict(lambda: {'total': 0, 'errors': 0, 'warnings': 0})
        self.recent_logs = deque(maxlen=100)
        
    def discover_log_files(self):
        """Find all log files"""
        if not self.log_dir.exists():
            print(f"❌ Log directory not found: {self.log_dir}")
            return []
        
        log_files = list(self.log_dir.glob('*.log'))
        # Exclude backup files
        log_files = [f for f in log_files if not re.search(r'\.\d{4}-\d{2}-\d{2}', f.name)]
        return log_files
    
    def follow_file(self, filepath):
        """Tail a file like tail -f"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Go to end of file
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    if line:
                        yield line
                    else:
                        time.sleep(0.1)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    def parse_log_line(self, line):
        """Parse log line and extract components"""
        # Pattern: 2025-12-15 10:30:45 - module - LEVEL - message
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (\S+) - (\w+) - (.+)'
        match = re.match(pattern, line)
        
        if match:
            timestamp, component, level, message = match.groups()
            return {
                'timestamp': timestamp,
                'component': component.split('.')[-1],  # Get last part
                'level': level,
                'message': message.strip()
            }
        return None
    
    def format_log(self, log_data, filename):
        """Format log entry with colors"""
        component = log_data['component']
        level = log_data['level']
        
        # Get colors
        level_color = LEVEL_COLORS.get(level, RESET)
        comp_color = COMPONENT_COLORS.get(component, RESET)
        
        # Emoji for levels
        emoji_map = {
            'DEBUG': '🔍',
            'INFO': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🔥'
        }
        emoji = emoji_map.get(level, '📝')
        
        # Format output
        time_str = log_data['timestamp'].split()[1]  # Just time part
        output = (
            f"{DIM}{time_str}{RESET} "
            f"{emoji} {level_color}{level:8}{RESET} "
            f"{comp_color}[{component:15}]{RESET} "
            f"{log_data['message']}"
        )
        
        return output
    
    def print_header(self):
        """Print dashboard header"""
        print("\033[2J\033[H")  # Clear screen
        print(f"{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}📊 RAG System - Real-time Log Monitor{RESET}")
        print(f"{BOLD}{'='*80}{RESET}")
        print()
    
    def print_stats(self):
        """Print statistics"""
        print(f"{BOLD}📈 Statistics:{RESET}")
        for component, stats in sorted(self.stats.items()):
            error_color = '\033[31m' if stats['errors'] > 0 else '\033[32m'
            warn_color = '\033[33m' if stats['warnings'] > 0 else '\033[32m'
            
            print(f"  {component:20} | "
                  f"Total: {stats['total']:4} | "
                  f"{error_color}Errors: {stats['errors']:3}{RESET} | "
                  f"{warn_color}Warnings: {stats['warnings']:3}{RESET}")
        print()
    
    def monitor(self, tail_lines=20):
        """Start monitoring logs"""
        log_files = self.discover_log_files()
        
        if not log_files:
            print("❌ No log files found")
            return
        
        print(f"📂 Monitoring {len(log_files)} log files:")
        for f in log_files:
            print(f"   • {f.name}")
        print()
        print("Press Ctrl+C to stop")
        print()
        time.sleep(2)
        
        # Show recent logs first
        print(f"{BOLD}📜 Recent logs ({tail_lines} lines):{RESET}")
        print("-" * 80)
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = deque(f, tail_lines)
                    for line in lines:
                        log_data = self.parse_log_line(line)
                        if log_data:
                            print(self.format_log(log_data, log_file.name))
            except Exception as e:
                print(f"⚠️  Error reading {log_file.name}: {e}")
        
        print()
        print(f"{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}🔴 LIVE MONITORING (new logs will appear below){RESET}")
        print(f"{BOLD}{'='*80}{RESET}")
        print()
        
        # Start monitoring (simplified version - just show last file)
        if log_files:
            main_log = log_files[0]  # Monitor first log file
            for line in self.follow_file(main_log):
                log_data = self.parse_log_line(line)
                if log_data:
                    # Update stats
                    comp = log_data['component']
                    self.stats[comp]['total'] += 1
                    if log_data['level'] == 'ERROR' or log_data['level'] == 'CRITICAL':
                        self.stats[comp]['errors'] += 1
                    elif log_data['level'] == 'WARNING':
                        self.stats[comp]['warnings'] += 1
                    
                    # Print log
                    print(self.format_log(log_data, main_log.name))
                    sys.stdout.flush()


def main():
    print()
    print("🚀 Starting Log Monitor...")
    print()
    
    monitor = LogMonitor()
    
    try:
        monitor.monitor(tail_lines=30)
    except KeyboardInterrupt:
        print()
        print()
        print("=" * 80)
        print("📊 Final Statistics:")
        print("=" * 80)
        monitor.print_stats()
        print()
        print("👋 Monitor stopped")
        print()


if __name__ == '__main__':
    main()
