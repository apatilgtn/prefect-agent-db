import os
import psycopg2
from psycopg2 import OperationalError, sql
from prefect import flow, task, get_run_logger
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

@task(retries=2, retry_delay_seconds=5)
def connect_db():
    """Connects to the PostgreSQL database."""
    logger = get_run_logger()
    try:
        logger.info(f"Attempting to connect to database '{os.getenv('DB_NAME')}' on {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
        )
        logger.info("Database connection successful.")
        return conn
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        raise

@task
def setup_db_table(conn):
    """Creates a sample table and inserts data if it doesn't exist."""
    logger = get_run_logger()
    cursor = conn.cursor()
    try:
        # Check if table exists
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sample_data');")
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            logger.info("Table 'sample_data' does not exist. Creating and populating...")
            cursor.execute("""
                CREATE TABLE sample_data (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50),
                    value INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            users_data = [('Alice', 100), ('Bob', 150), ('Charlie', 200)]
            insert_query = sql.SQL("INSERT INTO sample_data (name, value) VALUES (%s, %s)")
            cursor.executemany(insert_query, users_data)
            conn.commit()
            logger.info("Table 'sample_data' created and populated.")
        else:
            logger.info("Table 'sample_data' already exists.")
    except Exception as e:
        logger.error(f"Error during table setup: {e}")
        conn.rollback() # Rollback in case of error
        raise
    finally:
        cursor.close()


@task
def extract_data(conn, table_name: str = "sample_data"):
    """Extracts data from the specified table."""
    logger = get_run_logger()
    cursor = conn.cursor()
    try:
        query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name))
        logger.info(f"Executing query: {query.as_string(conn)}")
        cursor.execute(query)
        data = cursor.fetchall()
        logger.info(f"Extracted {len(data)} rows from '{table_name}'.")
        # Get column names
        colnames = [desc[0] for desc in cursor.description]
        # Convert to list of dicts
        result = [dict(zip(colnames, row)) for row in data]
        return result
    except Exception as e:
        logger.error(f"Error extracting data: {e}")
        raise
    finally:
        cursor.close()

@task
def transform_data(data: list):
    """Simple data transformation (e.g., add a processing timestamp)."""
    logger = get_run_logger()
    logger.info(f"Transforming {len(data)} records...")
    for record in data:
        record['processed_value'] = record.get('value', 0) * 1.1 # Example transformation
        record['processed_at_agent'] = time.time()
    logger.info("Transformation complete.")
    return data

@task
def load_data_simulated(data: list, output_filename: str = "output_data.txt"):
    """Simulates loading data by printing and writing to a file."""
    logger = get_run_logger()
    logger.info(f"Simulating load for {len(data)} records...")
    # Print to console (visible in agent logs)
    logger.info("--- Processed Data ---")
    for record in data[:5]: # Print first 5 records
         logger.info(record)
    if len(data) > 5:
        logger.info(f"... and {len(data) - 5} more records.")

    # Write to a local file (in the agent's environment)
    try:
        with open(output_filename, "w") as f:
            for record in data:
                f.write(str(record) + "\n")
        logger.info(f"Data successfully written to '{output_filename}' in agent environment.")
    except Exception as e:
        logger.error(f"Failed to write data to file: {e}")
        raise

@flow(name="Local DB ETL")
def local_db_etl_flow():
    """Main ETL flow orchestrated by Prefect, executed by the agent."""
    logger = get_run_logger()
    logger.info("Starting local DB ETL flow...")
    conn = None # Initialize conn to None
    try:
        conn = connect_db()
        setup_db_table(conn)
        raw_data = extract_data(conn)
        if raw_data: # Check if data was extracted
            transformed_data = transform_data(raw_data)
            load_data_simulated(transformed_data)
        else:
            logger.warning("No data extracted, skipping transform and load.")
    except Exception as e:
        logger.error(f"Flow execution failed: {e}")
        # Optionally re-raise the exception if you want the flow run to be marked as failed
        # raise
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")
    logger.info("Local DB ETL flow finished.")


if __name__ == "__main__":
    # Allows running the flow locally for testing without Prefect deployment/agent
    # Requires DB to be running and .env file present
    print("Running flow locally for testing...")
    local_db_etl_flow()
    print("Local execution finished. Check console and output_data.txt")
