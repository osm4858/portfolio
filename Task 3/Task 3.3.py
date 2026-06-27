"""
Task 1.04: Performance Analysis and Benchmarking - FIXED VERSION
Comprehensive performance testing between QuestDB and MongoDB with proper visualization
"""

import requests
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import json
import statistics
from typing import List, Dict, Any
import concurrent.futures
import numpy as np
import os

class PerformanceBenchmark:
    """Performance benchmarking tool for QuestDB vs MongoDB"""
    
    def __init__(self, api_base_url="http://localhost:5000"):
        self.api_base_url = api_base_url
        self.results = []
        
    def generate_test_scenarios(self) -> List[Dict]:
        """Generate different test scenarios"""
        scenarios = [
            # Small queries - Single day
            {
                "name": "Small Query - 1 Day",
                "start_time": "2024-01-15T00:00:00Z",
                "end_time": "2024-01-16T00:00:00Z", 
                "tickers": ["ADANIENT"],
                "fields": ["open", "high", "low", "close", "volume"],
                "expected_size": "small"
            },
            
            # Medium queries - 1 Week 
            {
                "name": "Medium Query - 1 Week",
                "start_time": "2024-01-15T00:00:00Z",
                "end_time": "2024-01-22T00:00:00Z",
                "tickers": ["ADANIENT"],
                "fields": ["open", "high", "low", "close", "volume"],
                "expected_size": "medium"
            },
            
            # Large queries - 1 Month
            {
                "name": "Large Query - 1 Month", 
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-02-01T00:00:00Z",
                "tickers": ["ADANIENT"],
                "fields": ["open", "high", "low", "close", "volume"],
                "expected_size": "large"
            },
            
            # Multiple fields test
            {
                "name": "All Fields Query",
                "start_time": "2024-01-15T00:00:00Z", 
                "end_time": "2024-01-16T00:00:00Z",
                "tickers": ["ADANIENT"],
                "fields": ["open", "high", "low", "close", "volume", "vwap"],
                "expected_size": "small"
            },
            
            # Different date ranges - using actual data range
            {
                "name": "Old Data Query",
                "start_time": "2015-02-02T00:00:00Z",
                "end_time": "2015-02-09T00:00:00Z", 
                "tickers": ["ADANIENT"],
                "fields": ["open", "high", "low", "close", "volume"],
                "expected_size": "medium"
            },
            
            # Recent data
            {
                "name": "Recent Data Query",
                "start_time": "2023-12-01T00:00:00Z",
                "end_time": "2023-12-31T00:00:00Z",
                "tickers": ["ADANIENT"], 
                "fields": ["open", "high", "low", "close", "volume"],
                "expected_size": "large"
            }
        ]
        
        return scenarios
    
    def make_api_request(self, endpoint: str, params: Dict) -> Dict:
        """Make API request and measure response time"""
        url = f"{self.api_base_url}{endpoint}"
        
        start_time = time.time()
        try:
            response = requests.get(url, params=params, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'response_time': end_time - start_time,
                    'server_query_time': data.get('query_time_seconds', 0),
                    'record_count': data.get('count', 0),
                    'data_size_kb': len(response.content) / 1024,
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False,
                    'response_time': end_time - start_time,
                    'error': f"HTTP {response.status_code}: {response.text[:200]}",
                    'status_code': response.status_code,
                    'record_count': 0,
                    'server_query_time': 0
                }
                
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            return {
                'success': False,
                'response_time': end_time - start_time,
                'error': str(e),
                'status_code': 0,
                'record_count': 0,
                'server_query_time': 0
            }
    
    def run_single_benchmark(self, scenario: Dict, iterations: int = 3) -> Dict:
        """Run benchmark for a single scenario"""
        print(f"📊 Running: {scenario['name']}")
        
        # Prepare request parameters
        params = {
            'start_time': scenario['start_time'],
            'end_time': scenario['end_time'],
            'tickers': ','.join(scenario['tickers']),
            'fields': ','.join(scenario['fields'])
        }
        
        # Test both databases
        questdb_results = []
        mongodb_results = []
        
        for i in range(iterations):
            print(f"   Iteration {i+1}/{iterations}")
            
            # Test QuestDB
            questdb_result = self.make_api_request('/api/market-data/questdb', params)
            questdb_results.append(questdb_result)
            time.sleep(0.5)  # Small delay between requests
            
            # Test MongoDB
            mongodb_result = self.make_api_request('/api/market-data/mongodb', params) 
            mongodb_results.append(mongodb_result)
            time.sleep(0.5)
        
        # Calculate statistics
        def calc_stats(results):
            if not results:
                return {
                    'success_rate': 0,
                    'avg_response_time': 0,
                    'avg_query_time': 0,
                    'avg_record_count': 0,
                    'errors': ['No results']
                }
            
            successful_results = [r for r in results if r.get('success', False)]
            
            if not successful_results:
                return {
                    'success_rate': 0,
                    'avg_response_time': 0,
                    'avg_query_time': 0,
                    'avg_record_count': 0,
                    'errors': [r.get('error', 'Unknown error') for r in results]
                }
            
            return {
                'success_rate': len(successful_results) / len(results) * 100,
                'avg_response_time': statistics.mean([r['response_time'] for r in successful_results]),
                'min_response_time': min([r['response_time'] for r in successful_results]),
                'max_response_time': max([r['response_time'] for r in successful_results]),
                'avg_query_time': statistics.mean([r.get('server_query_time', 0) for r in successful_results]),
                'avg_record_count': statistics.mean([r.get('record_count', 0) for r in successful_results]),
                'avg_data_size_kb': statistics.mean([r.get('data_size_kb', 0) for r in successful_results]),
                'std_response_time': statistics.stdev([r['response_time'] for r in successful_results]) if len(successful_results) > 1 else 0,
                'errors': [r.get('error', 'Unknown error') for r in results if not r.get('success')]
            }
        
        questdb_stats = calc_stats(questdb_results)
        mongodb_stats = calc_stats(mongodb_results)
        
        # Performance comparison
        comparison = {}
        if questdb_stats['success_rate'] > 0 and mongodb_stats['success_rate'] > 0:
            if questdb_stats['avg_response_time'] < mongodb_stats['avg_response_time']:
                speedup = mongodb_stats['avg_response_time'] / questdb_stats['avg_response_time']
                comparison = {
                    'faster_database': 'QuestDB',
                    'speedup_factor': round(speedup, 2),
                    'time_difference': round(mongodb_stats['avg_response_time'] - questdb_stats['avg_response_time'], 4)
                }
            else:
                speedup = questdb_stats['avg_response_time'] / mongodb_stats['avg_response_time']
                comparison = {
                    'faster_database': 'MongoDB', 
                    'speedup_factor': round(speedup, 2),
                    'time_difference': round(questdb_stats['avg_response_time'] - mongodb_stats['avg_response_time'], 4)
                }
        
        result = {
            'scenario': scenario,
            'questdb': questdb_stats,
            'mongodb': mongodb_stats,
            'comparison': comparison,
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    def run_comprehensive_benchmark(self) -> List[Dict]:
        """Run comprehensive benchmark suite"""
        print("🚀 Starting Comprehensive Performance Benchmark")
        print("=" * 60)
        
        scenarios = self.generate_test_scenarios()
        results = []
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n📋 Scenario {i}/{len(scenarios)}: {scenario['name']}")
            result = self.run_single_benchmark(scenario, iterations=3)
            results.append(result)
            
            # Show quick summary
            if result['comparison']:
                faster_db = result['comparison']['faster_database']
                speedup = result['comparison']['speedup_factor']
                print(f"   ⚡ Winner: {faster_db} ({speedup}x faster)")
            
            print(f"   📊 QuestDB: {result['questdb']['avg_response_time']:.4f}s avg")
            print(f"   🍃 MongoDB: {result['mongodb']['avg_response_time']:.4f}s avg")
        
        self.results = results
        return results
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        if not self.results:
            return {"error": "No benchmark results available"}
        
        report = {
            'summary': {
                'total_scenarios': len(self.results),
                'timestamp': datetime.now().isoformat()
            },
            'database_performance': {
                'questdb': {
                    'total_scenarios_won': 0,
                    'avg_response_times': [],
                    'avg_query_times': [],
                    'success_rates': []
                },
                'mongodb': {
                    'total_scenarios_won': 0,
                    'avg_response_times': [],
                    'avg_query_times': [], 
                    'success_rates': []
                }
            },
            'detailed_results': []
        }
        
        # Analyze results
        for result in self.results:
            # Count wins
            if result.get('comparison', {}).get('faster_database') == 'QuestDB':
                report['database_performance']['questdb']['total_scenarios_won'] += 1
            elif result.get('comparison', {}).get('faster_database') == 'MongoDB':
                report['database_performance']['mongodb']['total_scenarios_won'] += 1
            
            # Collect performance metrics
            if result['questdb']['success_rate'] > 0:
                report['database_performance']['questdb']['avg_response_times'].append(
                    result['questdb']['avg_response_time']
                )
                report['database_performance']['questdb']['avg_query_times'].append(
                    result['questdb']['avg_query_time']
                )
                report['database_performance']['questdb']['success_rates'].append(
                    result['questdb']['success_rate']
                )
            
            if result['mongodb']['success_rate'] > 0:
                report['database_performance']['mongodb']['avg_response_times'].append(
                    result['mongodb']['avg_response_time']
                )
                report['database_performance']['mongodb']['avg_query_times'].append(
                    result['mongodb']['avg_query_time']
                )
                report['database_performance']['mongodb']['success_rates'].append(
                    result['mongodb']['success_rate']
                )
            
            # Add to detailed results
            report['detailed_results'].append({
                'scenario_name': result['scenario']['name'],
                'questdb_time': result['questdb']['avg_response_time'],
                'mongodb_time': result['mongodb']['avg_response_time'],
                'winner': result.get('comparison', {}).get('faster_database', 'N/A'),
                'speedup': result.get('comparison', {}).get('speedup_factor', 'N/A'),
                'record_count': result['questdb'].get('avg_record_count', 0) or result['mongodb'].get('avg_record_count', 0)
            })
        
        # Calculate overall statistics
        for db in ['questdb', 'mongodb']:
            db_data = report['database_performance'][db]
            if db_data['avg_response_times']:
                db_data['overall_avg_response_time'] = statistics.mean(db_data['avg_response_times'])
                db_data['overall_avg_query_time'] = statistics.mean(db_data['avg_query_times'])
                db_data['overall_success_rate'] = statistics.mean(db_data['success_rates'])
        
        return report

    def save_results_to_files(self, base_filename: str = "benchmark_results"):
        """Save results to JSON and CSV files"""
        # Save detailed JSON results
        json_filename = f"{base_filename}.json"
        with open(json_filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"📄 Detailed results saved to {json_filename}")
        
        # Create CSV summary
        csv_data = []
        for result in self.results:
            csv_data.append({
                'Scenario': result['scenario']['name'],
                'QuestDB_Response_Time': result['questdb']['avg_response_time'],
                'QuestDB_Success_Rate': result['questdb']['success_rate'],
                'MongoDB_Response_Time': result['mongodb']['avg_response_time'],
                'MongoDB_Success_Rate': result['mongodb']['success_rate'],
                'Winner': result.get('comparison', {}).get('faster_database', 'N/A'),
                'Speedup_Factor': result.get('comparison', {}).get('speedup_factor', 'N/A'),
                'Record_Count': result['questdb'].get('avg_record_count', 0) or result['mongodb'].get('avg_record_count', 0)
            })
        
        csv_filename = f"{base_filename}.csv"
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_filename, index=False)
        print(f"📊 Summary CSV saved to {csv_filename}")
        
        return json_filename, csv_filename

    def create_visualizations(self):
        """Create comprehensive visualizations"""
        if not self.results:
            print("❌ No results to visualize")
            return
        
        try:
            # Set up the plotting style
            plt.style.use('default')
            sns.set_palette("Set2")
            
            # Create figure with subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('QuestDB vs MongoDB Performance Comparison', fontsize=16, fontweight='bold')
            
            # Prepare data for plotting
            scenarios = [r['scenario']['name'] for r in self.results]
            questdb_times = [r['questdb']['avg_response_time'] for r in self.results]
            mongodb_times = [r['mongodb']['avg_response_time'] for r in self.results]
            
            # 1. Bar chart - Response times by scenario
            x = np.arange(len(scenarios))
            width = 0.35
            
            axes[0, 0].bar(x - width/2, questdb_times, width, label='QuestDB', alpha=0.8, color='skyblue')
            axes[0, 0].bar(x + width/2, mongodb_times, width, label='MongoDB', alpha=0.8, color='lightgreen')
            
            axes[0, 0].set_xlabel('Scenarios')
            axes[0, 0].set_ylabel('Response Time (seconds)')
            axes[0, 0].set_title('Response Time by Scenario')
            axes[0, 0].set_xticks(x)
            axes[0, 0].set_xticklabels(scenarios, rotation=45, ha='right')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
            
            # 2. Box plot - Distribution comparison
            box_data = [questdb_times, mongodb_times]
            box_labels = ['QuestDB', 'MongoDB']
            
            bp = axes[0, 1].boxplot(box_data, labels=box_labels, patch_artist=True,
                                   boxprops=dict(facecolor='lightblue', color='blue'),
                                   medianprops=dict(color='red'))
            
            # Color the boxes
            colors = ['lightblue', 'lightgreen']
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
            
            axes[0, 1].set_ylabel('Response Time (seconds)')
            axes[0, 1].set_title('Response Time Distribution')
            axes[0, 1].grid(True, alpha=0.3)
            
            # 3. Speedup factor chart
            speedup_factors = []
            for result in self.results:
                if result.get('comparison', {}).get('faster_database') == 'QuestDB':
                    speedup_factors.append(result['comparison']['speedup_factor'])
                else:
                    speedup_factors.append(1.0)  # MongoDB wins or no comparison
            
            axes[1, 0].bar(scenarios, speedup_factors, alpha=0.7, color='orange')
            axes[1, 0].axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Baseline (1x)')
            axes[1, 0].set_xlabel('Scenarios')
            axes[1, 0].set_ylabel('Speedup Factor (x)')
            axes[1, 0].set_title('QuestDB Speedup Factor vs MongoDB')
            axes[1, 0].set_xticklabels(scenarios, rotation=45, ha='right')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
            
            # 4. Overall performance summary
            overall_questdb = statistics.mean(questdb_times) if questdb_times else 0
            overall_mongodb = statistics.mean(mongodb_times) if mongodb_times else 0
            
            databases = ['QuestDB', 'MongoDB']
            times = [overall_questdb, overall_mongodb]
            colors = ['skyblue', 'lightgreen']
            
            bars = axes[1, 1].bar(databases, times, color=colors, alpha=0.8)
            axes[1, 1].set_ylabel('Average Response Time (seconds)')
            axes[1, 1].set_title('Overall Performance Comparison')
            axes[1, 1].grid(True, alpha=0.3)
            
            # Add value labels on bars
            for bar, time_val in zip(bars, times):
                height = bar.get_height()
                axes[1, 1].text(bar.get_x() + bar.get_width()/2., height + 0.001,
                               f'{time_val:.4f}s', ha='center', va='bottom')
            
            # Adjust layout
            plt.tight_layout()
            plt.subplots_adjust(top=0.93)
            
            # Save the figure
            plt.savefig('performance_analysis.png', dpi=300, bbox_inches='tight')
            plt.savefig('performance_analysis.pdf', bbox_inches='tight')
            
            print("✅ Visualizations created and saved as 'performance_analysis.png'")
            
            # Show the plot
            plt.show()
            
        except Exception as e:
            print(f"❌ Error creating visualizations: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main benchmark execution"""
    print("🏁 Market Data Performance Benchmark - FIXED VERSION")
    print("=" * 60)
    
    # Initialize benchmark
    benchmark = PerformanceBenchmark()
    
    # Check API health
    try:
        response = requests.get(f"{benchmark.api_base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy and ready")
        else:
            print(f"⚠️  API health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Make sure your Flask API is running on localhost:5000")
        return
    
    # Run comprehensive benchmark
    try:
        results = benchmark.run_comprehensive_benchmark()
        
        # Generate report
        print("\n📋 Generating Performance Report...")
        report = benchmark.generate_performance_report()
        
        # Print summary
        print("\n🏆 BENCHMARK RESULTS SUMMARY")
        print("=" * 40)
        print(f"Total Scenarios: {report['summary']['total_scenarios']}")
        print(f"QuestDB Wins: {report['database_performance']['questdb']['total_scenarios_won']}")
        print(f"MongoDB Wins: {report['database_performance']['mongodb']['total_scenarios_won']}")
        
        if 'overall_avg_response_time' in report['database_performance']['questdb']:
            questdb_avg = report['database_performance']['questdb']['overall_avg_response_time']
            print(f"QuestDB Average Response Time: {questdb_avg:.4f}s")
        
        if 'overall_avg_response_time' in report['database_performance']['mongodb']:
            mongodb_avg = report['database_performance']['mongodb']['overall_avg_response_time']
            print(f"MongoDB Average Response Time: {mongodb_avg:.4f}s")
        
        # Save results
        print("\n💾 Saving Results...")
        json_file, csv_file = benchmark.save_results_to_files()
        
        # Create visualizations
        print("\n📊 Creating Visualizations...")
        benchmark.create_visualizations()
        
        print("\n✅ Performance Analysis Complete!")
        print(f"📄 Results saved to: {json_file}, {csv_file}")
        print("📊 Charts saved as: performance_analysis.png")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
