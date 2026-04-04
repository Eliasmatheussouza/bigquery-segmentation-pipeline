## dynamic SQL script for ETL process
DECLARE start_date DATE DEFAULT DATE_SUB(CURRENT_DATE(), INTERVAL 20 DAY);
DECLARE end_date DATE DEFAULT DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);

CREATE TEMP TABLE campaign_segment AS (
  SELECT
    email,
    document AS cpf
  FROM `project.dataset.table`
);

CREATE TEMP TABLE customer_id AS (

  ## Step 1: rank ORDERS by customer, most recent first
  SELECT
    LPAD(COALESCE(A.customer, A.document), 11, '0') AS cpf,
    A.order_id,
    A.product_qty,
    A.order_line_total_value,
    DENSE_RANK() OVER (
      PARTITION BY LPAD(COALESCE(A.customer, A.document), 11, '0')
      ORDER BY MAX(A.order_date) OVER (PARTITION BY A.order_id) DESC
    ) AS order_rank
  FROM `project.dataset.table` A
  LEFT JOIN (
    SELECT DISTINCT
      LPAD(REGEXP_REPLACE(CAST(cpf AS STRING), r'\D', ''), 11, '0') AS cpf
    FROM `project.dataset.table`
  ) B
    ON LPAD(REGEXP_REPLACE(CAST(A.customer AS STRING), r'\D', ''), 11, '0') = B.cpf
  WHERE A.customer IS NOT NULL
    AND B.cpf IS NULL
    AND DATE(A.order_date) BETWEEN start_date AND end_date
    AND store_id NOT IN (1001, 1002, 1003, 1004, 1005) ## excluding specific stores
    AND order_canceled_flag = 'N'
)

## Step 2: filter only the most recent order and aggregate ALL its lines
SELECT
  cpf,
  SUM(product_qty)            AS order_items,
  SUM(order_line_total_value) AS purchase_value
FROM ranked_orders
WHERE order_rank = 1
GROUP BY cpf
);

CREATE OR REPLACE TABLE `project.dataset.table` AS

SELECT
  campaign_segment.email,
  customer_id.order_items,
  customer_id.purchase_value
FROM
  campaign_segment
JOIN
  customer_id
USING (cpf)
