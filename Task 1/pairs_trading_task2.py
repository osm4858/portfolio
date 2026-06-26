# Task 2: Statistical Arbitrage Analysis
# This script implements correlation analysis, clustering, and mean-reversion strategy

import pandas as pd
import numpy as np
from pymongo import MongoClient
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.tsa.stattools import coint
from statsmodels.regression.linear_model import OLS
import warnings
warnings.filterwarnings('ignore')

class StatisticalArbitrageAnalyzer:
    def __init__(self, mongodb_uri="mongodb://localhost:27017/", db_name="sse_trading"):
        """
        Initialize the analyzer with database connection
        """
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
        self.collection = self.db.stock_data
        
        self.price_data = None
        self.returns_data = None
        self.correlation_matrix = None
        self.clusters = None
        
    def load_data(self, start_date="2015-01-01", end_date="2023-12-31"):
        """
        Load stock price data from MongoDB
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
        """
        print("Loading data from database...")
        
        # Get all tickers
        tickers = self.collection.distinct("ticker")
        print(f"Found {len(tickers)} tickers")
        
        # Load data for all tickers
        price_data = {}
        
        for ticker in tickers:
            query = {
                'ticker': ticker,
                'date': {'$gte': start_date, '$lte': end_date}
            }
            
            cursor = self.collection.find(query, {'_id': 0, 'date': 1, 'close': 1}).sort('date', 1)
            data = list(cursor)
            
            if len(data) > 100:  # Only include stocks with sufficient data
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                price_data[ticker] = df['close']
        
        # Create price dataframe
        self.price_data = pd.DataFrame(price_data)
        self.price_data = self.price_data.dropna()  # Remove rows with missing data
        
        # Calculate returns
        self.returns_data = self.price_data.pct_change().dropna()
        
        print(f"Loaded data for {len(self.price_data.columns)} stocks")
        print(f"Date range: {self.price_data.index[0]} to {self.price_data.index[-1]}")
        
    def build_correlation_matrix(self):
        """
        Step A: Build correlation matrix between stocks
        """
        print("\nStep A: Building correlation matrix...")
        
        if self.returns_data is None:
            raise ValueError("Data not loaded. Run load_data() first.")
        
        # Calculate correlation matrix
        self.correlation_matrix = self.returns_data.corr()
        
        # Remove self-correlations
        np.fill_diagonal(self.correlation_matrix.values, np.nan)
        
        # Display statistics
        corr_values = self.correlation_matrix.values.flatten()
        corr_values = corr_values[~np.isnan(corr_values)]
        
        print(f"Correlation Statistics:")
        print(f"Mean: {np.mean(corr_values):.4f}")
        print(f"Std: {np.std(corr_values):.4f}")
        print(f"Min: {np.min(corr_values):.4f}")
        print(f"Max: {np.max(corr_values):.4f}")
        
        return self.correlation_matrix
    
    def plot_correlation_heatmap(self, top_n=20):
        """
        Plot correlation heatmap for visualization
        """
        plt.figure(figsize=(12, 10))
        
        # Select top N stocks by trading volume or market cap (simplified)
        top_stocks = self.correlation_matrix.columns[:top_n]
        corr_subset = self.correlation_matrix.loc[top_stocks, top_stocks]
        
        sns.heatmap(corr_subset, annot=False, cmap='coolwarm', center=0,
                   square=True, linewidths=0.1)
        plt.title(f'Stock Correlation Heatmap (Top {top_n} Stocks)')
        plt.tight_layout()
        plt.show()
    
    def cluster_stocks(self, n_clusters=5, method='kmeans'):
        """
        Step B: Build clustering model to group stocks by correlations
        
        Args:
            n_clusters: Number of clusters
            method: Clustering method ('kmeans')
        """
        print(f"\nStep B: Clustering stocks into {n_clusters} groups...")
        
        if self.correlation_matrix is None:
            raise ValueError("Correlation matrix not built. Run build_correlation_matrix() first.")
        
        # Use correlation matrix as features for clustering
        # Convert correlation to distance matrix
        distance_matrix = 1 - np.abs(self.correlation_matrix.fillna(0))
        
        # Standardize the data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(distance_matrix)
        
        # Apply K-means clustering
        if method == 'kmeans':
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(scaled_data)
            
            # Calculate silhouette score
            silhouette_avg = silhouette_score(scaled_data, cluster_labels)
            print(f"Silhouette Score: {silhouette_avg:.4f}")
        
        # Create cluster mapping
        self.clusters = pd.DataFrame({
            'ticker': self.correlation_matrix.index,
            'cluster': cluster_labels
        })
        
        # Display cluster information
        cluster_counts = self.clusters['cluster'].value_counts().sort_index()
        print("\nCluster Distribution:")
        for cluster_id, count in cluster_counts.items():
            print(f"Cluster {cluster_id}: {count} stocks")
            cluster_stocks = self.clusters[self.clusters['cluster'] == cluster_id]['ticker'].tolist()
            print(f"  Stocks: {cluster_stocks[:5]}{'...' if len(cluster_stocks) > 5 else ''}")
        
        return self.clusters
    
    def find_cointegrated_pairs(self, cluster_id=None, significance_level=0.05):
        """
        Find cointegrated pairs within clusters or overall
        
        Args:
            cluster_id: Specific cluster to analyze (None for all)
            significance_level: P-value threshold for cointegration test
        """
        print(f"\nFinding cointegrated pairs (p-value < {significance_level})...")
        
        if cluster_id is not None:
            if self.clusters is None:
                raise ValueError("Clusters not built. Run cluster_stocks() first.")
            tickers = self.clusters[self.clusters['cluster'] == cluster_id]['ticker'].tolist()
            print(f"Analyzing cluster {cluster_id} with {len(tickers)} stocks")
        else:
            tickers = list(self.price_data.columns)
        
        cointegrated_pairs = []
        
        for i in range(len(tickers)):
            for j in range(i+1, len(tickers)):
                ticker1, ticker2 = tickers[i], tickers[j]
                
                # Get price series
                series1 = self.price_data[ticker1].dropna()
                series2 = self.price_data[ticker2].dropna()
                
                # Align series
                common_dates = series1.index.intersection(series2.index)
                if len(common_dates) < 100:  # Require sufficient data
                    continue
                
                s1 = series1.loc[common_dates]
                s2 = series2.loc[common_dates]
                
                # Cointegration test
                try:
                    score, p_value, _ = coint(s1, s2)
                    
                    if p_value < significance_level:
                        # Calculate hedge ratio using OLS
                        model = OLS(s1, s2).fit()
                        hedge_ratio = model.params[0]
                        
                        cointegrated_pairs.append({
                            'ticker1': ticker1,
                            'ticker2': ticker2,
                            'p_value': p_value,
                            'hedge_ratio': hedge_ratio,
                            'correlation': self.correlation_matrix.loc[ticker1, ticker2]
                        })
                except:
                    continue
        
        cointegrated_pairs = pd.DataFrame(cointegrated_pairs)
        cointegrated_pairs = cointegrated_pairs.sort_values('p_value')
        
        print(f"Found {len(cointegrated_pairs)} cointegrated pairs")
        
        return cointegrated_pairs
    
    def design_mean_reversion_strategy(self, ticker1, ticker2, hedge_ratio, 
                                     entry_threshold=2.0, exit_threshold=0.5):
        """
        Step C: Design mean-reversion strategy for a stock pair
        
        Args:
            ticker1, ticker2: Stock pair tickers
            hedge_ratio: Hedge ratio from cointegration analysis
            entry_threshold: Z-score threshold for entry (in standard deviations)
            exit_threshold: Z-score threshold for exit
        """
        print(f"\nStep C: Designing mean-reversion strategy for {ticker1} vs {ticker2}")
        
        # Get price series
        series1 = self.price_data[ticker1].dropna()
        series2 = self.price_data[ticker2].dropna()
        
        # Align series
        common_dates = series1.index.intersection(series2.index)
        s1 = series1.loc[common_dates]
        s2 = series2.loc[common_dates]
        
        # Calculate spread
        spread = s1 - hedge_ratio * s2
        
        # Calculate rolling statistics for z-score
        window = 60  # 60-day rolling window
        spread_mean = spread.rolling(window=window).mean()
        spread_std = spread.rolling(window=window).std()
        z_score = (spread - spread_mean) / spread_std
        
        # Generate trading signals
        signals = pd.DataFrame(index=common_dates)
        signals['spread'] = spread
        signals['z_score'] = z_score
        signals['position'] = 0
        
        # Entry signals
        signals.loc[z_score > entry_threshold, 'position'] = -1  # Short spread (sell stock1, buy stock2)
        signals.loc[z_score < -entry_threshold, 'position'] = 1   # Long spread (buy stock1, sell stock2)
        
        # Exit signals
        signals.loc[np.abs(z_score) < exit_threshold, 'position'] = 0
        
        # Forward fill positions to maintain them until exit
        signals['position'] = signals['position'].replace(0, np.nan).fillna(method='ffill').fillna(0)
        
        strategy_data = {
            'ticker1': ticker1,
            'ticker2': ticker2,
            'hedge_ratio': hedge_ratio,
            'signals': signals,
            'entry_threshold': entry_threshold,
            'exit_threshold': exit_threshold
        }
        
        return strategy_data
    
    def backtest_strategy(self, strategy_data, transaction_cost=0.001):
        """
        Step D: Backtest the mean-reversion strategy
        
        Args:
            strategy_data: Strategy data from design_mean_reversion_strategy()
            transaction_cost: Transaction cost as fraction of trade value
        """
        print(f"\nStep D: Backtesting strategy...")
        
        ticker1 = strategy_data['ticker1']
        ticker2 = strategy_data['ticker2']
        hedge_ratio = strategy_data['hedge_ratio']
        signals = strategy_data['signals'].copy()
        
        # Get price data
        s1 = self.price_data[ticker1].loc[signals.index]
        s2 = self.price_data[ticker2].loc[signals.index]
        
        # Calculate returns
        r1 = s1.pct_change()
        r2 = s2.pct_change()
        
        # Calculate strategy returns
        signals['position_change'] = signals['position'].diff()
        signals['strategy_return'] = signals['position'].shift(1) * (r1 - hedge_ratio * r2)
        
        # Apply transaction costs
        signals['transaction_costs'] = np.abs(signals['position_change']) * transaction_cost
        signals['net_return'] = signals['strategy_return'] - signals['transaction_costs']
        
        # Calculate cumulative performance
        signals['cumulative_return'] = (1 + signals['net_return'].fillna(0)).cumprod()
        
        # Performance metrics
        total_return = signals['cumulative_return'].iloc[-1] - 1
        annual_return = (signals['cumulative_return'].iloc[-1] ** (252 / len(signals))) - 1
        volatility = signals['net_return'].std() * np.sqrt(252)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        # Maximum drawdown
        rolling_max = signals['cumulative_return'].expanding().max()
        drawdown = (signals['cumulative_return'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Number of trades
        num_trades = signals['position_change'].abs().sum() / 2  # Divide by 2 for round trips
        
        # Win rate
        positive_returns = signals['net_return'][signals['net_return'] > 0]
        negative_returns = signals['net_return'][signals['net_return'] < 0]
        win_rate = len(positive_returns) / (len(positive_returns) + len(negative_returns))
        
        results = {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'signals': signals
        }
        
        print(f"\nBacktest Results:")
        print(f"Total Return: {total_return:.2%}")
        print(f"Annual Return: {annual_return:.2%}")
        print(f"Volatility: {volatility:.2%}")
        print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"Max Drawdown: {max_drawdown:.2%}")
        print(f"Number of Trades: {num_trades:.0f}")
        print(f"Win Rate: {win_rate:.2%}")
        
        return results
    
    def plot_strategy_performance(self, backtest_results, strategy_data):
        """
        Plot strategy performance charts
        """
        signals = backtest_results['signals']
        ticker1 = strategy_data['ticker1']
        ticker2 = strategy_data['ticker2']
        
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        
        # Plot 1: Spread and Z-score
        ax1 = axes[0]
        ax1.plot(signals.index, signals['spread'], label='Spread', color='blue')
        ax1.set_ylabel('Spread')
        ax1.set_title(f'Spread: {ticker1} - {strategy_data["hedge_ratio"]:.2f} * {ticker2}')
        ax1.legend()
        ax1.grid(True)
        
        ax1_twin = ax1.twinx()
        ax1_twin.plot(signals.index, signals['z_score'], label='Z-Score', color='red', alpha=0.7)
        ax1_twin.axhline(y=strategy_data['entry_threshold'], color='red', linestyle='--', alpha=0.5)
        ax1_twin.axhline(y=-strategy_data['entry_threshold'], color='red', linestyle='--', alpha=0.5)
        ax1_twin.axhline(y=strategy_data['exit_threshold'], color='green', linestyle='--', alpha=0.5)
        ax1_twin.axhline(y=-strategy_data['exit_threshold'], color='green', linestyle='--', alpha=0.5)
        ax1_twin.set_ylabel('Z-Score')
        ax1_twin.legend(loc='upper right')
        
        # Plot 2: Positions
        axes[1].plot(signals.index, signals['position'], label='Position', color='orange', linewidth=2)
        axes[1].set_ylabel('Position')
        axes[1].set_title('Trading Positions')
        axes[1].legend()
        axes[1].grid(True)
        
        # Plot 3: Cumulative returns
        axes[2].plot(signals.index, signals['cumulative_return'], label='Strategy', color='green', linewidth=2)
        axes[2].set_ylabel('Cumulative Return')
        axes[2].set_xlabel('Date')
        axes[2].set_title('Strategy Performance')
        axes[2].legend()
        axes[2].grid(True)
        
        plt.tight_layout()
        plt.show()

# Example usage and workflow
def run_complete_analysis():
    """
    Run the complete statistical arbitrage analysis workflow
    """
    print("=== Statistical Arbitrage Analysis Workflow ===")
    
    # Initialize analyzer
    analyzer = StatisticalArbitrageAnalyzer()
    
    # Load data
    analyzer.load_data(start_date="2020-01-01", end_date="2023-12-31")
    
    # Step A: Build correlation matrix
    correlation_matrix = analyzer.build_correlation_matrix()
    
    # Step B: Cluster stocks
    clusters = analyzer.cluster_stocks(n_clusters=5)
    
    # Find cointegrated pairs
    pairs = analyzer.find_cointegrated_pairs(significance_level=0.05)
    
    if len(pairs) > 0:
        # Select the best pair (lowest p-value)
        best_pair = pairs.iloc[0]
        ticker1 = best_pair['ticker1']
        ticker2 = best_pair['ticker2']
        hedge_ratio = best_pair['hedge_ratio']
        
        print(f"\nAnalyzing best pair: {ticker1} vs {ticker2}")
        print(f"P-value: {best_pair['p_value']:.6f}")
        print(f"Hedge ratio: {hedge_ratio:.4f}")
        print(f"Correlation: {best_pair['correlation']:.4f}")
        
        # Step C: Design strategy
        strategy = analyzer.design_mean_reversion_strategy(
            ticker1, ticker2, hedge_ratio,
            entry_threshold=2.0, exit_threshold=0.5
        )
        
        # Step D: Backtest strategy
        results = analyzer.backtest_strategy(strategy, transaction_cost=0.001)
        
        # Plot results
        analyzer.plot_strategy_performance(results, strategy)
        
        return analyzer, results, strategy
    else:
        print("No cointegrated pairs found with current parameters")
        return analyzer, None, None

if __name__ == "__main__":
    # Make sure you have run Task 1 first to populate the database
    print("Starting Statistical Arbitrage Analysis")
    print("Make sure Task 1 data system is set up and database is populated")
    
    analyzer, results, strategy = run_complete_analysis()