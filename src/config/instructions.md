# SingleStore MCP Server — Agent Instructions

You are connected to the SingleStore MCP Server, which lets you manage and interact with SingleStore Helios (cloud) databases.

## SingleStore Cloud Structure

### Organizations

An **organization** is the top-level account boundary. All resources (workspace groups, databases, users) belong to an organization. A user may have access to multiple organizations. You must select an organization at the start of a session before doing anything else.

### Workspace Groups

A **workspace group** is a logical grouping of compute workspaces within a region (e.g. AWS us-east-1). All workspaces in a group share access to the same set of databases and the same **Stage** storage.

### Workspaces (Dedicated)

A **workspace** is an individual compute pool inside a workspace group. Each workspace has its own endpoint for SQL connections. Multiple workspaces in the same group can access the same databases.

### Starter Workspaces (Shared)

A **starter workspace** (also called shared or virtual workspace) is a free-tier, single-node workspace with its own built-in database and Stage storage. Unlike dedicated workspaces, starter workspaces are not part of a workspace group — they are standalone. They have resource limits (e.g. storage caps) and some features are unavailable (e.g. `LOAD DATA STAGE` SQL command).

### Stage (File Storage)

**Stage** is an attached file storage service (up to 10 GB) for organizing files before importing them into a database, or handling them in Notebooks. Each workspace group and each starter workspace has its own Stage. You can:

- Upload, list, move, and delete files and folders via the Management API.
- Ingest data from Stage into tables using either:
  - `LOAD DATA STAGE 'file.csv' INTO TABLE t ...` (dedicated workspaces only, SingleStore 8.9+).
  - ```
    CREATE PIPELINE p AS LOAD DATA STAGE 'file.csv' 
    SKIP DUPLICATE KEY ERRORS INTO TABLE t 
    FIELDS TERMINATED BY ',' IGNORE 1 LINES;
    START PIPELINE p;
    ```
  - The Cloud Portal's "Load To Database" flow, which generates a notebook.
- Access Stage files from within notebooks for data processing.

Supported file formats: CSV, JSON, Parquet, GZ, Snappy.

Since Stage lives in a specific workspace group or starter workspace (henceforth described as "deployment"), you must first understand what deployment's Stage the user intends to interact with. You may use `list_starter_workspaces` or `workspace_groups_info` for this purpose. If there is only one deployment, use that by default. If the user's intent is clear, use the more appropriate deployment, and if it's not clear, clarify with the user which deployment they'd like to use (given the deployment list you have fetched).

**Important:**
 - Stage API calls use the **workspace group ID** (for dedicated) or the **starter workspace ID** (for shared) — not the individual workspace ID.
 - When loading JSON files, they are expected to be in a ND-JSON format (newline-delimited).

 If you need any aditional information related to loading data from stage you can refer to: https://docs.singlestore.com/cloud/load-data/load-data-from-files/stage.md

### Notebooks

**Notebooks** are Jupyter environments (Python + SQL) that run inside workspace groups. They connect directly to the databases in their workspace group, so you can query data, transform it, and visualize results — all in one place. Notebooks can also be scheduled as recurring jobs via the Job Service for automated workflows.

In Notebooks you may use SingleStore's Python Client (`singlestoredb`) to create and use SQL connections and make management API calls. You may find more information in the [package's documentation](https://singlestoredb-python.labs.singlestore.com/api.html).

**Example 1:**

```python
# Fetching a file from Stage
import singlestoredb as s2
import json
mgr=s2.manage_workspaces()

# Use the starter workspace stage
stage=mgr.starter_workspaces[0].stage

# Or use a specific workspace group / starter workspace.
starter_workspace_dict = {ws.id: ws for ws in mgr.starter_workspaces}
workspace_group_dict = {ws.id: ws for ws in mgr.workspace_groups}

stage = starter_workspace_dict.get("aaaaaa-bbbbbb-cccccc").stage

# Fetch file
file_content = stage.download_file('file.json').decode("utf-8")
file_content_2 = stage.download_file('folder/file.json').decode("utf-8")

# List directory
dir_root = stage.listdir()
dir_folder = stage.listdir("folder_name")

# Execute SQL
conn = s2.connect()
cur = conn.cursor()
cur.execute('select * from table')

# Fetch the results
print(cur.description)
for item in cur:
    print(item)
```

**Example 2:**

You may also use SQL blocks, or in-line SQL in Python blocks to execute queries directly.

```python
%%SQL
SHOW TABLES;
```

```python
table_query_result = %sql show tables;
```

## Documentation

If you have web navigation tooling available, you may use [SingleStore Documentation](https://docs.singlestore.com/llms.txt) as a starting point.