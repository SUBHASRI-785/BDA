from pyspark.sql import SparkSession
from pyspark.ml.fpm import FPGrowth
from pyspark.sql.functions import collect_set


# ============================================================
# CREATE SPARK SESSION
# ============================================================

spark = SparkSession.builder \
    .appName("MarketMartRecommendation") \
    .master("local[*]") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("\n======================================")
print("   MARKETMART RECOMMENDATION ENGINE")
print("======================================\n")


# ============================================================
# LOAD TRANSACTION DATA
# ============================================================

file_path = "data/marketmart_transactions_5000.csv"

transactions = spark.read \
    .option("header", True) \
    .option("inferSchema", True) \
    .csv(file_path)

print("Transaction dataset loaded successfully!")


# ============================================================
# CREATE TRANSACTION BASKETS
# ============================================================

baskets = transactions.groupBy(
    "TransactionID"
).agg(
    collect_set("ProductID").alias("items")
)

print("Transaction baskets created successfully!")


# ============================================================
# FP-GROWTH
# ============================================================

fp_growth = FPGrowth(
    itemsCol="items",
    minSupport=0.01,
    minConfidence=0.20
)

print("Training FP-Growth model...")

model = fp_growth.fit(baskets)

print("FP-Growth model trained successfully!")


# ============================================================
# ASSOCIATION RULES
# ============================================================

rules = model.associationRules

print("\n======================================")
print("       ASSOCIATION RULES")
print("======================================\n")

rules.select(
    "antecedent",
    "consequent",
    "confidence",
    "lift"
).show(
    30,
    truncate=False
)


# ============================================================
# SAVE RULES AS CSV
# ============================================================

rules.select(
    "antecedent",
    "consequent",
    "confidence",
    "lift"
).write \
    .mode("overwrite") \
    .option("header", True) \
    .csv("data/association_rules_csv")


print("\nAssociation rules generated successfully!")

print("\n======================================")
print("       STEP 8 COMPLETED")
print("======================================\n")

spark.stop()