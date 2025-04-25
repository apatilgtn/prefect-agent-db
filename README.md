# Prefect Agent DB Access Example

This project demonstrates how to use a Prefect Agent to execute a data pipeline (flow) that needs to access a local PostgreSQL database, simulating an on-premise or private network resource.

**Architecture:**

1.  **Prefect Cloud/Server (Control Plane):** Orchestrates the workflow, manages schedules, and monitors runs. Resides outside the private network.
2.  **Local Machine (Execution Plane):**
    *   Runs the PostgreSQL database (simulated private resource).
    *   Runs the **Prefect Agent**. The agent polls Prefect Cloud/Server for flow runs assigned to its work pool.
    *   When a run is assigned, the agent downloads the flow code (if needed) and executes it locally, allowing it to access the local PostgreSQL database.

**Prerequisites:**

*   Docker and Docker Compose
*   Python 3.8+ and `pip`
*   A Prefect Cloud account (or a self-hosted Prefect server instance)
*   Git

**Setup:**

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd prefect-agent-db-example
    ```

2.  **Create and Populate `.env` File:**
    *   Copy the contents from the example section above into a new file named `.env` in the project root.
    *   **Crucially:** Update `PREFECT_API_URL` and `PREFECT_API_KEY` with your actual Prefect Cloud credentials. You can create an API key in your Prefect Cloud profile settings.
    *   Verify the `DB_*` variables match `docker-compose.yml`.

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Start the Local PostgreSQL Database:**
    ```bash
    docker-compose up -d
    ```
    *(Wait a few seconds for the database to initialize)*

5.  **Log in to Prefect Cloud (CLI):**
    ```bash
    prefect cloud login --key YOUR_PREFECT_CLOUD_API_KEY --workspace YOUR_WORKSPACE_NAME # Or use interactive login
    ```
    *(Replace with your API key and workspace handle)*

6.  **Create a Prefect Work Pool:**
    This pool is where the agent will look for work. We'll use a 'process' type pool, meaning the agent runs flows as local subprocesses.
    ```bash
    # Get the pool name from your .env file or type it directly
    POOL_NAME=$(grep PREFECT_WORK_POOL_NAME .env | cut -d '=' -f2 | tr -d '"')
    prefect work-pool create "$POOL_NAME" --type process
    # Example: prefect work-pool create "local-db-agent-pool" --type process
    ```
    *Note: If the pool already exists, this command might give an error, which is fine.*

7.  **Start the Prefect Agent:**
    Open a **new terminal** in the project directory. This terminal will run the agent process.
    ```bash
    # Make sure your .env file is loaded or Prefect settings are configured
    # The agent needs API URL/Key to communicate
    POOL_NAME=$(grep PREFECT_WORK_POOL_NAME .env | cut -d '=' -f2 | tr -d '"')
    prefect agent start -p "$POOL_NAME"
    # Example: prefect agent start -p "local-db-agent-pool"
    ```
    *Leave this terminal running. You should see the agent start polling for work.*

8.  **Deploy the Flow:**
    In your **original terminal**, deploy the flow to Prefect Cloud, associating it with the work pool your agent is watching.
    ```bash
    POOL_NAME=$(grep PREFECT_WORK_POOL_NAME .env | cut -d '=' -f2 | tr -d '"')
    prefect deploy --name "Local DB ETL Deployment" --flow-path flows/etl_flow.py --flow-name "Local DB ETL" -p "$POOL_NAME" --description "Deployment for the local DB ETL flow"
    # Example: prefect deploy --name "Local DB ETL Deployment" --flow-path flows/etl_flow.py --flow-name "Local DB ETL" -p "local-db-agent-pool"
    ```
    *This uploads metadata about your flow to Prefect Cloud, telling it how and where (which pool) to run it.*

9.  **Trigger a Flow Run:**
    *   Go to your Prefect Cloud UI.
    *   Navigate to "Flow Runs" or "Deployments".
    *   Find your "Local DB ETL Deployment".
    *   Click "Run" (or the play button) to trigger a manual run.

**Observe:**

*   In the **agent terminal**, you should see logs indicating it picked up the flow run and started executing the tasks.
*   You'll see log messages from the flow, including connection attempts, data extraction info, and the simulated load output.
*   In the **Prefect Cloud UI**, you can monitor the flow run's progress and view logs.
*   Check the project directory for the `output_data.txt` file created by the agent.

**Cleanup:**

1.  Stop the agent (Ctrl+C in the agent terminal).
2.  Stop and remove the database container:
    ```bash
    docker-compose down -v # -v removes the volume
    ```
