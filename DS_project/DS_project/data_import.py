import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from datetime import datetime

def clean_data(df):
    """Clean and prepare the data for import"""
    # Remove any leading/trailing whitespace
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Clean the 'No of Reviews' column by extracting just the number
    df['No of Reviews'] = df['No of Reviews'].str.extract('(\d+)').fillna(0).astype(int)
    
    # Clean the 'Reviews' column to be a float
    df['Reviews'] = pd.to_numeric(df['Reviews'], errors='coerce')
    
    # Replace NaN values in 'Reviews' with a default value
    df['Reviews'] = df['Reviews'].fillna(0.0)
    
    # Ensure price range is standardized
    df['Price_Range'] = df['Price_Range'].fillna('Not Available')
    
    # Clean up the Type column by removing extra spaces
    df['Type'] = df['Type'].str.strip()
    
    return df

def create_table(conn):
    """Create the restaurants table in TimescaleDB"""
    with conn.cursor() as cur:
        try:
            # First, check if TimescaleDB extension is enabled
            cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
            conn.commit()
            
            # Drop the table if it exists
            cur.execute("DROP TABLE IF EXISTS restaurants;")
            conn.commit()
            
            # Create the base table without primary key constraint
            cur.execute("""
                CREATE TABLE restaurants (
                    id INTEGER,
                    name VARCHAR(255),
                    street_address VARCHAR(255),
                    location VARCHAR(255),
                    type VARCHAR(255),
                    rating FLOAT,
                    review_count INTEGER,
                    contact_number VARCHAR(50),
                    trip_advisor_url TEXT,
                    menu TEXT,
                    price_range VARCHAR(50),
                    city VARCHAR(100),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            conn.commit()
            
            # Convert to TimescaleDB hypertable
            cur.execute("""
                SELECT create_hypertable('restaurants', 'created_at', 
                                       if_not_exists => TRUE,
                                       migrate_data => TRUE);
            """)
            conn.commit()
            
            # Create a non-unique index on id and created_at
            cur.execute("""
                CREATE INDEX idx_restaurants_id_created 
                ON restaurants (id, created_at DESC);
            """)
            
            # Create an index on city for better query performance
            cur.execute("""
                CREATE INDEX idx_restaurants_city 
                ON restaurants (city, created_at DESC);
            """)
            conn.commit()
            
            print("Table and indexes created successfully")
            
        except Exception as e:
            print(f"Error in create_table: {e}")
            conn.rollback()
            raise e

def import_data(conn, df):
    """Import the cleaned data into TimescaleDB"""
    with conn.cursor() as cur:
        try:
            # Prepare the data as a list of tuples
            values = [
                (idx,  # Use the index as the id
                 row['Name'], 
                 row['Street Address'], 
                 row['Location'], 
                 row['Type'], 
                 row['Reviews'], 
                 row['No of Reviews'],
                 row['Contact Number'], 
                 row['Trip_advisor Url'], 
                 row['Menu'], 
                 row['Price_Range'], 
                 row['City'],
                 datetime.now())
                for idx, (_, row) in enumerate(df.iterrows(), start=1)
            ]
            
            # Insert the data using execute_values
            execute_values(cur, """
                INSERT INTO restaurants (
                    id, name, street_address, location, type, rating, 
                    review_count, contact_number, trip_advisor_url,
                    menu, price_range, city, created_at
                ) VALUES %s;
            """, values)
            
            conn.commit()
            print(f"Imported {len(values)} records successfully")
            
        except Exception as e:
            print(f"Error in import_data: {e}")
            conn.rollback()
            raise e

def main():
    # Database connection parameters
    db_params = {
        'dbname': 'restaurant_db',
        'user': 'jh',
        'password': '12345678',
        'host': 'localhost',
        'port': '5432'
    }
    
    try:
        # Read the CSV file
        df = pd.read_csv('dataset/reviews_data.csv', sep=';')
        print("CSV file read successfully")
        
        # Clean the data
        df_cleaned = clean_data(df)
        print("Data cleaned successfully")
        
        # Connect to the database
        conn = psycopg2.connect(**db_params)
        print("Connected to database successfully")
        
        # Create the table
        create_table(conn)
        
        # Import the data
        import_data(conn, df_cleaned)
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()