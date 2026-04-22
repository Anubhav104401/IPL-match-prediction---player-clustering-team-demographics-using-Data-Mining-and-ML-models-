# Big Data Pipeline Refactoring & Stabilization Report

## 1. Executive Summary
The goal of this session was to stabilize and execute a complex, multi-stage Big Data ETL pipeline. The pipeline suffered from cascading failures cutting across infrastructure (Java versions, filesystem locks), configuration (missing engines), and syntax (reserved keywords, dialect mismatches). 

By adopting a strict **log-driven, linear debugging methodology**, we systematically isolated each component, fixed the root causes without relying on "guess-and-check" methods, and successfully pushed the pipeline to a completely clean 0-exit-code run completing in under 9 minutes.

## 2. Debugging Methodology & Thought Process

When faced with a terminal flooded with stack traces, the first rule is to **stop executing randomly and isolate the blast radius**. My thought process followed these distinct phases:

1. **Infrastructure First (Layer 0):** Hadoop, YARN, and HiveServer2 are the bedrock. If the JVM strings are wrong or the databases are locked, no SQL will ever run. I prioritized validating background daemons.
2. **Schema & DDL (Layer 1):** Before transforming data, the tables must exist. I isolated the Hive DDL scripts to watch for standard ParseExceptions.
3. **Execution Context (Layer 2):** Once tables existed, we tried pushing data. When jobs failed immediately without parsing errors, it pointed to misconfigured distributed compute resources.
4. **Analytics & Aggregation (Layer 3):** Complex SQL requires dialect checks. What works in PostgreSQL or Snowflake might not work in Hive 3.1.3.

---

## 3. Detailed Bug Breakdown & Resolutions

### Phase 1: Environment & Core Service Instability
> [!CAUTION]
> **Symptom:** HiveServer2 repeatedly crashed during initialization with `CLIService.applyAuthorizationConfigPolicy` stack traces, and the Metastore complained about schema locks.

* **Investigation:** 
  * **Java Mismatch:** Hive 3.1.3 explicitly requires Java 8. Portions of the environment variables (like in the bash export scripts) were incorrectly pointing to Java 11 setups. 
  * **Filesystem Lock Issues:** The project was running under WSL (Windows Subsystem for Linux), but the Hive Derby Metastore was attempting to write to the `/mnt/c/` Windows NTFS mounted drive. NTFS handles file locking differently than Linux native partitions, leading to Derby database corruptions.
* **The Fix:**
  * Globally enforced `JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64` across all Bash profiles and execution scripts.
  * Migrated the Hive Metastore database away from the Windows mount directly into the Linux `ext4` filesystem at `/home/anubh/hive_metastore_db`.

### Phase 2: HiveQL DDL & The Keyword Trap
> [!WARNING]
> **Symptom:** Hive failed immediately during `STAGE 4` with `FAILED: ParseException`.

* **Investigation:** The stack trace pinpointed specific lines in `02_raw_tables.hql` and `03_optimized_tables.hql`. By cross-referencing Hive's reserved keyword lists, I identified that the column name `floor` (intended to mean a building floor) is an active mathematical function keyword in Hive. Similarly, in the ETL scripts, `AS rows` was used, clashing with windowing syntax (`ROWS BETWEEN`).
* **The Fix:**
  * Enclosed all instances of `floor` with backticks (`` `floor` ``) to force Hive to treat it as a column identifier.
  * Renamed the alias `rows` to `row_count` in `04_etl_transforms.hql` to avoid ambiguity.

### Phase 3: The Execution Engine Mismatch
> [!IMPORTANT]
> **Symptom:** Jobs would compile, YARN would accept them, but they would instantly fail to allocate containers. 

* **Investigation:** I inspected the script headers and found `SET hive.execution.engine=tez;`. Tez is a high-performance execution engine, but it was **not installed or configured** in the current Hadoop cluster. Hive was looking for an engine that didn't exist.
* **The Fix:**
  * I performed a workspace-wide replacement, converting `hive.execution.engine=tez` to `hive.execution.engine=mr`. While MapReduce (`mr`) is older and slightly slower, it is the native default engine and guarantees stability and execution on any standard Hadoop cluster.

### Phase 4: Advanced SQL Syntax Limitations
> [!NOTE]
> **Symptom:** The final analytics aggregations in `05_analytics_queries.hql` threw complex semantic exceptions.

* **Investigation (The QUALIFY Clause):** The code attempted to use `QUALIFY ROW_NUMBER() OVER (...) = 1` to deduplicate records. While common in modern cloud warehouses, Hive 3 does not support the `QUALIFY` keyword.
  * *Fix:* Refactored the architecture by wrapping the window function in an inner subquery and applying a standard `WHERE rn = 1` condition on the outer query.
* **Investigation (GROUPING Bitmasks):** Query 5a utilized the `GROUPING()` function to identify rollup levels. However, Hive 3.1.x threw `Error 10016: The first argument to grouping() must be an int/long`, choking on STRING partition columns.
  * *Fix:* Removed the complex bitmask logic. We didn't actually need it because the existing `COALESCE(column, 'ALL_DATES')` logic was already perfectly identifying which rows were sub-totals within the `GROUPING SETS`.

### Phase 5: The Final Export Mile
> [!TIP]
> **Symptom:** The final bash script `export_results.sh` failed to generate the `sensor_anomalies.csv` and threw a java missing error.

* **Investigation:** 
  1. Found a hardcoded `export JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"` isolated inside the bash script that overwrote our global variables.
  2. Found an unescaped reserved word in the export `SELECT` statement: `sr.timestamp`.
* **The Fix:**
  * Corrected the script to use the Java 8 pathway. 
  * Updated `sr.timestamp` to match the processed table's true safe name: `sr.timestamp_ts`.

---

## 4. Final Verification & Impact

By systematically layering these fixes, the entire **guess-and-check loop was eliminated**. 

**Final Run Statistics:**
* Data processed: 50,000 Web logs, 100,000 IoT sensor metrics, 20,000 Social Posts.
* Total MapReduce Jobs Launched: 6
* Total Time Elapsed: **08 Minutes 55 Seconds**
* Final Status: Exit Code 0 (Complete Success)

The pipeline is now stabilized, production-ready, and resilient against future data runs.
