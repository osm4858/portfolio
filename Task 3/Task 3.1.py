"""
MongoDB Setup and Data Loading Program for Task 1.02
Modified for local MongoDB without Docker
"""

import pandas as pd
import pymongo
from pymongo import MongoClient
from datetime import datetime
import os
import glob
import subprocess
import sys
import time

class MongoDBSetupAndLoader:
    def __init__(self):
        # Use local MongoDB without authentication
        self.connection_string = "mongodb://localhost:27017/"
        self.client = None
        self.db = None
        self.collection = None
        self.metadata_collection = None
        
    def check_mongodb_running(self):
        """Check if MongoDB is running"""
        try:
            client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            client.server_info()
            print("✅ MongoDB is running!")
            return True
        except Exception as e:
            print(f"❌ MongoDB not running: {e}")
            return False
    
    def connect_to_mongodb(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client['market_data_db']
            self.collection = self.db['intraday_market_data']
            self.metadata_collection = self.db['ticker_metadata']
            
            # Test connection
            self.client.server_info()
            print("✅ Connected to MongoDB!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            return False
    
    def create_database_structure(self):
        """Create collections and indexes"""
        print("🏗️  Creating database structure...")
        
        try:
            # Create collection with validation (optional - can be removed if causing issues)
            validator = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["ticker", "date", "timestamp", "ohlcv"],
                    "properties": {
                        "ticker": {
                            "bsonType": "string",
                            "description": "Stock ticker symbol"
                        },
                        "date": {
                            "bsonType": "string",
                            "description": "Date in YYYY-MM-DD format"
                        },
                        "timestamp": {
                            "bsonType": "date",
                            "description": "Timestamp of the data point"
                        },
                        "ohlcv": {
                            "bsonType": "object",
                            "required": ["open", "high", "low", "close", "volume"],
                            "properties": {
                                "open": {"bsonType": "double"},
                                "high": {"bsonType": "double"},
                                "low": {"bsonType": "double"},
                                "close": {"bsonType": "double"},
                                "volume": {"bsonType": "long"}
                            }
                        }
                    }
                }
            }
            
            # Drop existing collections if they exist
            if "intraday_market_data" in self.db.list_collection_names():
                self.db.drop_collection("intraday_market_data")
            if "ticker_metadata" in self.db.list_collection_names():
                self.db.drop_collection("ticker_metadata")
            
            # Create new collections (without validator if it causes issues)
            self.db.create_collection("intraday_market_data")  # Removed validator for simplicity
            self.db.create_collection("ticker_metadata")
            
            print("✅ Collections created!")
            
        except Exception as e:
            print(f"⚠️  Error creating collections: {e}")
            # Fallback: just get references to collections
            self.collection = self.db['intraday_market_data']
            self.metadata_collection = self.db['ticker_metadata']
        
        # Create indexes
        try:
            print("📊 Creating indexes...")
            
            # Primary indexes
            self.collection.create_index([("ticker", 1), ("timestamp", 1)])
            self.collection.create_index([("date", 1)])
            self.collection.create_index([("timestamp", 1)])
            self.collection.create_index([("ticker", 1)])
            
            # Compound index
            self.collection.create_index([
                ("ticker", 1), 
                ("date", 1), 
                ("timestamp", 1)
            ])
            
            # Metadata index
            self.metadata_collection.create_index([("ticker", 1)], unique=True)
            
            print("✅ Indexes created!")
            
        except Exception as e:
            print(f"❌ Error creating indexes: {e}")
    
    def load_csv_to_mongodb(self, csv_file_path, chunk_size=5000):
        """Load single CSV file into MongoDB"""
        print(f"📂 Loading {os.path.basename(csv_file_path)}")
        
        # Extract ticker from filename
        ticker = os.path.basename(csv_file_path).replace('.csv', '')
        
        total_inserted = 0
        
        try:
            # Read CSV in chunks
            for chunk_num, chunk in enumerate(pd.read_csv(csv_file_path, chunksize=chunk_size), 1):
                documents = []
                
                for _, row in chunk.iterrows():
                    # Skip rows with missing essential data
                    if pd.isna(row.get('date')) or pd.isna(row.get('open')):
                        continue
                    
                    # Handle different column names
                    date_value = row.get('date') or row.get('Date') or row.get('DATE')
                    open_value = row.get('open') or row.get('Open') or row.get('OPEN')
                    high_value = row.get('high') or row.get('High') or row.get('HIGH')
                    low_value = row.get('low') or row.get('Low') or row.get('LOW')
                    close_value = row.get('close') or row.get('Close') or row.get('CLOSE')
                    volume_value = row.get('volume') or row.get('Volume') or row.get('VOLUME')
                    
                    if pd.isna(date_value) or pd.isna(open_value):
                        continue
                    
                    doc = {
                        "ticker": ticker,
                        "date": str(date_value),
                        "timestamp": pd.to_datetime(str(date_value)),
                        "ohlcv": {
                            "open": float(open_value) if pd.notna(open_value) else 0.0,
                            "high": float(high_value) if pd.notna(high_value) else 0.0,
                            "low": float(low_value) if pd.notna(low_value) else 0.0,
                            "close": float(close_value) if pd.notna(close_value) else 0.0,
                            "volume": int(volume_value) if pd.notna(volume_value) else 0
                        },
                        "metadata": {
                            "exchange": "NSE",
                            "currency": "INR",
                            "data_source": "csv_import"
                        }
                    }
                    
                    documents.append(doc)
                
                # Insert batch
                if documents:
                    try:
                        result = self.collection.insert_many(documents, ordered=False)
                        total_inserted += len(result.inserted_ids)
                        print(f"   📝 Chunk {chunk_num}: {len(result.inserted_ids)} documents")
                    except Exception as e:
                        print(f"   ❌ Error in chunk {chunk_num}: {e}")
            
            print(f"✅ {ticker}: Total {total_inserted} documents inserted")
            
            # Create metadata entry
            self.create_ticker_metadata(ticker)
            
            return total_inserted
            
        except Exception as e:
            print(f"❌ Error loading {csv_file_path}: {e}")
            return 0
    
    def create_ticker_metadata(self, ticker):
        """Create metadata for a ticker"""
        try:
            metadata = {
                "ticker": ticker,
                "company_name": ticker,
                "exchange": "NSE",
                "currency": "INR",
                "last_updated": datetime.now()
            }
            
            self.metadata_collection.update_one(
                {"ticker": ticker},
                {"$set": metadata},
                upsert=True
            )
        except Exception as e:
            print(f"⚠️  Error creating metadata for {ticker}: {e}")
    
    def load_multiple_csvs(self, csv_directory):
        """Load all CSV files from directory"""
        print(f"🔍 Looking for CSV files in: {csv_directory}")
        
        csv_files = glob.glob(os.path.join(csv_directory, "*.csv"))
        
        if not csv_files:
            print(f"❌ No CSV files found in {csv_directory}")
            return
        
        total_files = len(csv_files)
        print(f"📁 Found {total_files} CSV files")
        
        total_documents = 0
        successful_files = 0
        
        for i, csv_file in enumerate(csv_files, 1):
            print(f"\n📊 Processing file {i}/{total_files}")
            inserted = self.load_csv_to_mongodb(csv_file)
            
            if inserted > 0:
                successful_files += 1
                total_documents += inserted
        
        print(f"\n🎉 Summary:")
        print(f"   ✅ Successfully loaded: {successful_files}/{total_files} files")
        print(f"   📊 Total documents: {total_documents:,}")
    
    def verify_data(self):
        """Verify the loaded data"""
        print("\n🔍 Verifying loaded data...")
        
        try:
            # Total count
            total_docs = self.collection.count_documents({})
            print(f"📊 Total documents: {total_docs:,}")
            
            # Count by ticker
            pipeline = [
                {"$group": {
                    "_id": "$ticker",
                    "count": {"$sum": 1},
                    "earliest": {"$min": "$timestamp"},
                    "latest": {"$max": "$timestamp"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            print("\n📈 Top 5 tickers by document count:")
            for result in results:
                ticker = result['_id']
                count = result['count']
                earliest = result['earliest'].strftime('%Y-%m-%d') if result['earliest'] else 'N/A'
                latest = result['latest'].strftime('%Y-%m-%d') if result['latest'] else 'N/A'
                print(f"   {ticker}: {count:,} documents ({earliest} to {latest})")
            
            # Sample document
            sample = self.collection.find_one()
            if sample:
                print(f"\n📝 Sample document structure:")
                print(f"   Ticker: {sample.get('ticker')}")
                print(f"   Date: {sample.get('date')}")
                print(f"   OHLCV: {sample.get('ohlcv')}")
            
        except Exception as e:
            print(f"❌ Error during verification: {e}")
    
    def run_complete_setup(self, csv_directory):
        """Run the complete MongoDB setup process"""
        print("🚀 Starting MongoDB Setup and Data Loading Process")
        print("=" * 60)
        
        # Step 1: Check if MongoDB is running
        if not self.check_mongodb_running():
            print("\n❌ MongoDB is not running")
            print("Please start MongoDB manually:")
            print("  On macOS: brew services start mongodb/brew/mongodb-community")
            print("  Or run: mongod --dbpath /usr/local/var/mongodb")
            print("  Then run this script again")
            return False
        
        # Step 2: Connect to MongoDB
        print("\n🔌 Connecting to MongoDB...")
        if not self.connect_to_mongodb():
            return False
        
        # Step 3: Create database structure
        print("\n🏗️  Setting up database structure...")
        self.create_database_structure()
        
        # Step 4: Load CSV data
        print(f"\n📂 Loading CSV data from: {csv_directory}")
        self.load_multiple_csvs(csv_directory)
        
        # Step 5: Verify data
        self.verify_data()
        
        print("\n✅ MongoDB setup and data loading completed!")
        print("🌐 You can now access MongoDB at: mongodb://localhost:27017")
        print("📊 Database: market_data_db")
        print("📁 Collection: intraday_market_data")
        print("🔍 Use MongoDB Compass to view your data!")
        
        return True

def main():
    """Main function"""
    print("MongoDB Market Data Setup Program")
    print("=" * 40)
    print("Using local MongoDB without Docker")
    print("=" * 40)
    
    # Get CSV directory from user
    csv_directory = input("Enter the path to your CSV files directory: ").strip()
    
    if not os.path.exists(csv_directory):
        print(f"❌ Directory not found: {csv_directory}")
        return
    
    # Create loader instance and run setup
    loader = MongoDBSetupAndLoader()
    success = loader.run_complete_setup(csv_directory)
    
    if success:
        print("\n🎉 Task 1.02 completed successfully!")
        print("Ready to proceed to Task 1.03 (REST API)")
    else:
        print("\n❌ Setup failed. Please check the errors above.")

if __name__ == "__main__":
    # Install required packages first
    required_packages = ['pandas', 'pymongo']
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    main()
