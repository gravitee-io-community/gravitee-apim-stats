# Gravitee APIM Statistics Exporter

A Python tool to export and analyze statistics from Gravitee API Management (APIM) instances. This tool fetches API data from the Gravitee Management API and exports comprehensive statistics in JSON format.

## Quick Start with Docker

### 1. Build the Docker Image

From the project root directory:

```bash
docker build -t gravitee-apim-stats:latest -f docker/Dockerfile .
```

### 2. Export Statistics with Bearer Token Authentication

Create the output directory and run the export:

```bash
mkdir -p output

docker run -it --rm \
  -v $(pwd)/output:/app/output \
  -e GRAVITEE_SERVER_URL="https://your-gravitee-server.com/management" \
  -e GRAVITEE_AUTH_TYPE="bearer" \
  -e GRAVITEE_TOKEN="your-bearer-token" \
  -e GRAVITEE_ORG_ID="your-organization-id" \
  -e GRAVITEE_ENV_ID="your-environment-id" \
  gravitee-apim-stats:latest \
  python src/export_apim_stats.py --json -o output/apis_stats.json
```

**Note:** Replace the environment variables with your actual values:
- `GRAVITEE_SERVER_URL`: Your Gravitee Management API base URL
- `GRAVITEE_TOKEN`: Your Bearer token
- `GRAVITEE_ORG_ID`: Your organization UUID (required for V2 APIs)
- `GRAVITEE_ENV_ID`: Your environment UUID

The JSON file will be saved in the `output/` directory on your host machine.

### 3. Display Statistics

Display the statistics from the exported JSON file:

```bash
docker run -it --rm \
  -v $(pwd)/output:/app/output \
  gravitee-apim-stats:latest \
  python src/display_stats.py -i output/apis_stats.json
```

This will display formatted statistics including:
- API statistics (by status, version, type, execution mode)
- User connection statistics
- Policies and resources usage
- TOP 10 APIs by request count

## Features

- **Export APIM Statistics**: Fetch API data from Gravitee Management API v2 and export statistics in JSON format
- **Comprehensive Statistics**: Includes API status, definition versions, types, execution modes, properties, response templates, plans, policies, and resources
- **Request Analytics**: Automatically fetches request counts per plan for the last 30 days
- **Multi-Version API Support**: Supports both V2 and V4 API definitions with appropriate endpoints
- **Authentication Methods**: Supports both Basic Auth and Bearer Token authentication
- **User Statistics**: Tracks user connection patterns (last 7, 30, 90, 180 days, never connected)
- **TOP 10 APIs**: Displays the top 10 APIs by request count
- **Pagination Support**: Automatically handles pagination to retrieve all APIs, users, and dictionaries
- **Multiple Output Formats**: Export to JSON file or display formatted statistics
- **Docker Support**: Fully containerized for easy deployment
- **Configuration Management**: Support for multiple environments via config files or environment variables

## Project Structure

```
.
├── src/
│   ├── export_apim_stats.py  # Main script to export APIM statistics
│   └── display_stats.py       # Script to display statistics from JSON
├── test/
│   └── test_export_apim_stats.py  # Test script
├── docker/
│   ├── Dockerfile             # Docker image definition
│   └── docker-compose.yml     # Docker Compose configuration
├── apim/
│   └── spec/                  # API specifications (v1 and v2)
├── output/                    # Generated JSON output files
├── config.json                # Main configuration file
└── requirements.txt           # Python dependencies
```

## Prerequisites

- Docker (for Docker usage)
- Python 3.9 or higher (for local usage)
- Access to a Gravitee Management API instance
- Valid credentials (username/password for Basic Auth or Bearer Token) for the Gravitee instance

## Configuration

### Using Environment Variables

**For Bearer Token Authentication (Recommended):**
```bash
export GRAVITEE_SERVER_URL="https://your-gravitee-server.com/management"
export GRAVITEE_AUTH_TYPE="bearer"
export GRAVITEE_TOKEN="your-bearer-token"
export GRAVITEE_ORG_ID="your-org-id"
export GRAVITEE_ENV_ID="your-env-id"
```

**For Basic Authentication:**
```bash
export GRAVITEE_SERVER_URL="https://your-gravitee-server.com/management"
export GRAVITEE_AUTH_TYPE="basic"
export GRAVITEE_USERNAME="your-username"
export GRAVITEE_PASSWORD="your-password"
export GRAVITEE_ORG_ID="DEFAULT"
export GRAVITEE_ENV_ID="DEFAULT"
```

### Using Configuration Files

Create a `config.json` file in the project root:

**For Bearer Token Authentication:**
```json
{
  "server_url": "https://your-gravitee-server.com/management",
  "auth_type": "bearer",
  "token": "your-bearer-token",
  "org_id": "your-organization-id",
  "env_id": "your-environment-id"
}
```

**For Basic Authentication:**
```json
{
  "server_url": "https://your-gravitee-server.com/management",
  "auth_type": "basic",
  "username": "your-username",
  "password": "your-password",
  "org_id": "DEFAULT",
  "env_id": "DEFAULT"
}
```

You can also create environment-specific config files (e.g., `config.master-env.json`, `config.demo-dev-nicolas.json`) and reference them with the `-c` flag.

**Note:** 
- `auth_type` defaults to `"basic"` if not specified
- For V2 APIs, the `org_id` must be the actual organization UUID (not "DEFAULT")
- Test configuration files (containing sensitive credentials) are ignored by git. See `.gitignore` for details.

## Local Installation

### Installation Steps

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd cmdb
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment:
   - Copy `env.example` to `.env` and update with your values, or
   - Create a `config.json` file (see Configuration section)

## Usage

### Export Statistics to JSON

Export all API statistics to a JSON file:

```bash
python src/export_apim_stats.py --json -o output/apis_stats.json
```

With a specific config file:

```bash
python src/export_apim_stats.py -c config.master-env.json --json -o output/apis_stats.json
```

### Display Statistics

Display statistics in a formatted table (non-JSON mode):

```bash
python src/export_apim_stats.py
```

Or display statistics from an existing JSON file:

```bash
python src/display_stats.py -i output/apis_stats.json
```

### Command Line Options

#### export_apim_stats.py

- `-c, --config`: Path to configuration file (default: `config.json` in project root)
- `-o, --output`: Output file path for JSON format (if not specified, outputs to stdout)
- `--json`: Output in JSON format instead of formatted table

#### display_stats.py

- `-i, --input`: Input JSON file (if not specified, reads from stdin)

## Docker Usage

### Using Docker Compose

1. Create the output directory:
   ```bash
   mkdir -p output
   ```

2. Set environment variables (optional, defaults are provided):
   
   **For Bearer Token:**
   ```bash
   export GRAVITEE_SERVER_URL="https://your-gravitee-server.com/management"
   export GRAVITEE_AUTH_TYPE="bearer"
   export GRAVITEE_TOKEN="your-bearer-token"
   export GRAVITEE_ORG_ID="your-org-id"
   export GRAVITEE_ENV_ID="your-env-id"
   ```
   
   **For Basic Auth:**
   ```bash
   export GRAVITEE_SERVER_URL="https://your-gravitee-server.com/management"
   export GRAVITEE_AUTH_TYPE="basic"
   export GRAVITEE_USERNAME="your-username"
   export GRAVITEE_PASSWORD="your-password"
   export GRAVITEE_ORG_ID="DEFAULT"
   export GRAVITEE_ENV_ID="DEFAULT"
   ```

3. Navigate to the docker directory and start the container:
   ```bash
   cd docker
   docker-compose up -d
   ```

4. Export statistics to JSON file:
   ```bash
   docker-compose exec gravitee-apim-stats python src/export_apim_stats.py --json -o output/apis_stats.json
   ```

5. Display statistics from the JSON file:
   ```bash
   docker-compose exec gravitee-apim-stats python src/display_stats.py -i output/apis_stats.json
   ```

6. Stop the container:
   ```bash
   docker-compose down
   ```

### Using Config Files with Docker

To use config files, mount them as volumes in `docker-compose.yml`:

```yaml
volumes:
  - ../output:/app/output
  - ../config.master-env.json:/app/config.master-env.json:ro
  - ../config.demo-dev-nicolas.json:/app/config.demo-dev-nicolas.json:ro
```

Then use them with the `-c` flag:
```bash
docker-compose exec gravitee-apim-stats python src/export_apim_stats.py \
  -c config.master-env.json \
  --json \
  -o output/apis_stats_master.json
```

**Note:** 
- The `output` directory is automatically mounted to persist JSON files between container executions
- JSON files will be accessible in the `output/` directory at the project root
- Config files must be mounted as volumes to be accessible inside the container

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GRAVITEE_SERVER_URL` | Base URL of the Gravitee Management API | `http://localhost:8083/management` |
| `GRAVITEE_AUTH_TYPE` | Authentication type: `basic` or `bearer` | `basic` |
| `GRAVITEE_USERNAME` | Username for Basic Auth | `admin` |
| `GRAVITEE_PASSWORD` | Password for Basic Auth | `admin` |
| `GRAVITEE_TOKEN` | Bearer token for Bearer Auth | - |
| `GRAVITEE_ORG_ID` | Organization ID | `DEFAULT` |
| `GRAVITEE_ENV_ID` | Environment ID | `DEFAULT` |

## API Version Support

The tool supports both V2 and V4 API definitions:

- **V2 APIs**: Uses `/organizations/{orgId}/environments/{envId}/apis/{apiId}/analytics` endpoint
- **V4 APIs**: Uses `/v2/environments/{envId}/apis/{apiId}/analytics` endpoint

The tool automatically detects the API definition version and uses the appropriate endpoint format. For V2 APIs, ensure that `org_id` in your configuration is the actual organization UUID (not "DEFAULT").

## Analytics

The tool automatically fetches request analytics for each API plan:
- **Time Period**: Last 30 days
- **Data Source**: Gravitee Analytics API
- **Format**: Request count per plan ID
- **Storage**: Stored in each plan as `requestCount30Days`

## Statistics Exported

The JSON output includes:

- **Total APIs count**
- **Per-API data**:
  - ID
  - Definition version (V2, V4, FEDERATED, etc.)
  - Type (PROXY, MESSAGE, NATIVE, etc.)
  - Execution mode (V3, V4_EMULATION_ENGINE, etc.)
  - State (STARTED, STOPPED)
  - Properties count
  - Dynamic properties count
  - Response templates count
  - GKO (Gravitee Kubernetes Operator) flag
  - Plans (with ID, status, security type, and **request count for last 30 days**)
  - Policies (list of enabled policies)
  - Resources (list of resource types)
- **Users data**:
  - ID
  - Last connection timestamp
- **Dictionaries data**:
  - ID
  - Type (manual/dynamic)
  - Properties count
- **Aggregated statistics**:
  - By status
  - By definition version
  - By type
  - By execution mode

## Output Format

The JSON output follows this structure:

```json
{
  "total_apis": 100,
  "apis": [
    {
      "id": "api-id",
      "definitionVersion": "V4",
      "type": "PROXY",
      "executionMode": "V4_EMULATION_ENGINE",
      "state": "STARTED",
      "propertiesCount": 5,
      "dynamicPropertiesCount": 2,
      "responseTemplatesCount": 3,
      "isGKO": false,
      "plans": [
        {
          "id": "plan-id",
          "status": "PUBLISHED",
          "type": "KEY_LESS",
          "requestCount30Days": 150
        }
      ],
      "policies": ["transform-headers", "rate-limit"],
      "resources": ["cache"]
    }
  ],
  "statistics": {
    "by_status": { "STARTED": 80, "STOPPED": 20 },
    "by_definition_version": { "V4": 60, "V2": 40 },
    "by_type": { "PROXY": 70, "MESSAGE": 30 },
    "by_execution_mode": { "V4_EMULATION_ENGINE": 50, "V3": 30, "N/A": 20 }
  },
  "total_users": 25,
  "users": [
    {
      "id": "user-id",
      "last_connection": 1763315149705
    }
  ],
  "total_dictionaries": 5,
  "dictionaries": [
    {
      "id": "dict-id",
      "type": "manual",
      "propertiesCount": 10
    }
  ]
}
```

## Displayed Statistics

When using `display_stats.py`, the following statistics are displayed:

- **API Statistics**:
  - By status (STARTED/STOPPED)
  - By definition version (V2/V4/FEDERATED)
  - By type (PROXY/MESSAGE/NATIVE)
  - By execution mode (V3/V4_EMULATION_ENGINE)
- **Users Statistics**:
  - By last connection period (7, 30, 90, 180 days, more than 180 days, never connected)
- **Policies Statistics**:
  - APIs with/without policies
  - Unique policies and their usage count
- **Resources Statistics**:
  - APIs with/without resources
  - Unique resources and their usage count
- **TOP 10 APIs**:
  - Ranked by total request count (last 30 days)
  - Shows API ID, total requests, and number of plans

## Testing

Run the test script to verify connection and functionality:

```bash
python test/test_export_apim_stats.py
```

The test script will:
1. Test connection to the Gravitee Management API
2. Verify authentication
3. Execute the export script with test configuration

## License

[Add your license information here]

## Contributing

[Add contributing guidelines here]
