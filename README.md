Segmentation Load — Off-Loyalty Customer Pipeline
This SQL pipeline is part of my daily work as an Analytics Engineer and has been anonymized for portfolio purposes.
The pipeline identifies customers who purchased in physical stores but are not enrolled in the loyalty program, and loads the results into a target table for downstream CDP activation.
It is split into two scripts:
intermediate_table.sql builds a staging layer using BigQuery temp tables and window functions (ROW_NUMBER, DENSE_RANK) to deduplicate transactions and isolate the most recent purchase per customer within a dynamic date range. Loyalty members are excluded via a LEFT JOIN anti-pattern against the loyalty dimension.
load_table.sql performs an upsert into the target table using a MERGE statement. The source is deduplicated with ROW_NUMBER() OVER (PARTITION BY email) to prevent the "must match at most one source row" error. Updates are conditionally applied using IS DISTINCT FROM to avoid unnecessary writes.
All project IDs, dataset names, and business-specific identifiers have been removed. The logic and structure reflect real production code.
