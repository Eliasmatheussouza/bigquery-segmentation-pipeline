MERGE INTO `project.dataset.table` AS target
USING (
  SELECT
    email,
    order_items,
    purchase_value
  FROM (
    SELECT
      email,
      order_items,
      purchase_value,
      ROW_NUMBER() OVER (
        PARTITION BY email
        ORDER BY purchase_value DESC
      ) AS rn
    FROM `project.dataset.table`
  )
  WHERE rn = 1
) AS source
ON target.email = source.email

WHEN MATCHED AND (
    target.order_items IS DISTINCT FROM source.order_items OR
    target.purchase_value  IS DISTINCT FROM source.purchase_value
)
THEN
  UPDATE SET
    target.order_items     = source.order_items,
    target.purchase_value     = source.purchase_value,
    target.updated_at = CURRENT_TIMESTAMP()

WHEN NOT MATCHED THEN
  INSERT (email, order_items, purchase_value, updated_at)
  VALUES (source.email, source.order_items, source.purchase_value, CURRENT_TIMESTAMP());