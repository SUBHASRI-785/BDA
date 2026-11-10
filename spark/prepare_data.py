
from pyspark.sql import SparkSession
from pyspark.sql.functions import collect_set

import csv
import os


# ============================================================
# 1. CREATE SPARK SESSION
# ============================================================

spark = SparkSession.builder \
    .appName("MarketMartDataPreparation") \
    .master("local[*]") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("\n======================================")
print("   MARKETMART BIG DATA PROCESSING")
print("======================================\n")


# ============================================================
# 2. LOAD TRANSACTION DATA
# ============================================================

file_path = "data/marketmart_transactions_5000.csv"

print("Loading transaction dataset...")

transactions = spark.read \
    .option("header", True) \
    .option("inferSchema", True) \
    .csv(file_path)

print("Transaction data loaded successfully!")


# ============================================================
# 3. DISPLAY SCHEMA
# ============================================================

print("\nDataset Schema:")
transactions.printSchema()


# ============================================================
# 4. DISPLAY SAMPLE DATA
# ============================================================

print("\nFirst 10 transactions:")

transactions.show(
    10,
    truncate=False
)


# ============================================================
# 5. COUNT RECORDS
# ============================================================

total_rows = transactions.count()

print("\nTotal transaction records:", total_rows)


# ============================================================
# 6. CREATE TRANSACTION BASKETS
# ============================================================

print("\nCreating transaction baskets...")

baskets = transactions.groupBy(
    "TransactionID"
).agg(
    collect_set("ProductID").alias("items")
)


# ============================================================
# 7. DISPLAY BASKETS
# ============================================================

print("\n======================================")
print("       TRANSACTION BASKETS")
print("======================================\n")

baskets.show(
    10,
    truncate=False
)


# ============================================================
# 8. COUNT UNIQUE TRANSACTIONS
# ============================================================

total_transactions = baskets.count()

print(
    "\nTotal unique transactions:",
    total_transactions
)


# ============================================================
# 9. COLLECT PREPARED DATA
# ============================================================

print("\nPreparing transaction data...")

basket_rows = baskets.collect()


# ============================================================
# 10. SAVE AS A NORMAL CSV FILE
# ============================================================

output_file = "data/prepared_transactions.csv"

print("\nSaving prepared transaction data...")

with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "TransactionID",
        "items"
    ])

    for row in basket_rows:

        transaction_id = row["TransactionID"]

        items = row["items"]

        items_text = ",".join(
            str(item) for item in items
        )

        writer.writerow([
            transaction_id,
            items_text
        ])


# ============================================================
# 11. VERIFY OUTPUT
# ============================================================

if os.path.exists(output_file):

    file_size = os.path.getsize(output_file)

    print("\nPrepared transaction data saved successfully!")

    print("Location:", output_file)

    print("File size:", file_size, "bytes")

else:

    print("\nERROR: Output file was not created.")


# ============================================================
# 12. FINISH
# ============================================================

print("\n======================================")
print("       STEP 6 COMPLETED")
print("======================================\n")


spark.stop()
