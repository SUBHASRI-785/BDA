from flask import Flask, render_template, session, redirect, url_for, request
import pandas as pd
import os
from datetime import datetime
import uuid


# ============================================================
# BASE PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

TEMPLATES_DIR = os.path.join(
    BASE_DIR,
    "templates"
)

STATIC_DIR = os.path.join(
    BASE_DIR,
    "static"
)


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

app.secret_key = "marketmart_secret_key_2026"


# ============================================================
# DATA FILES
# ============================================================

PRODUCT_FILE = os.path.join(
    DATA_DIR,
    "marketmart_product_catalog.csv"
)

RULES_FILE = os.path.join(
    DATA_DIR,
    "association_rules.csv"
)

TRANSACTION_FILE = os.path.join(
    DATA_DIR,
    "customer_purchases.csv"
)


# ============================================================
# LOAD PRODUCT CATALOG
# ============================================================

products_df = pd.read_csv(
    PRODUCT_FILE
)

products_df["ProductID"] = (
    products_df["ProductID"]
    .astype(str)
    .str.strip()
)


# ============================================================
# CUSTOMER ID
# ============================================================

CUSTOMER_ID = "C001"


# ============================================================
# PRODUCT IMAGE
# ============================================================

def get_product_image(product_name):

    from urllib.parse import quote

    return (
        "https://loremflickr.com/500/400/"
        + quote(str(product_name))
        + "?lock=1"
    )


# ============================================================
# GET CUSTOMER PURCHASES
# ============================================================

def get_customer_purchases():

    if not os.path.exists(
        TRANSACTION_FILE
    ):
        return set()

    try:

        purchases_df = pd.read_csv(
            TRANSACTION_FILE
        )

    except Exception:

        return set()

    if purchases_df.empty:

        return set()

    required_columns = [
        "CustomerID",
        "ProductID"
    ]

    for column in required_columns:

        if column not in purchases_df.columns:

            return set()

    customer_purchases = (
        purchases_df[
            purchases_df["CustomerID"]
            .astype(str)
            .str.strip()
            ==
            CUSTOMER_ID
        ]
    )

    if customer_purchases.empty:

        return set()

    purchased_products = set(
        customer_purchases[
            "ProductID"
        ]
        .astype(str)
        .str.strip()
        .tolist()
    )

    return purchased_products


# ============================================================
# GET CURRENT CART
# ============================================================

def get_cart_products():

    cart = session.get(
        "cart",
        []
    )

    return set(
        str(item).strip()
        for item in cart
    )


# ============================================================
# GET SEARCH PRODUCTS
# ============================================================

def get_search_products(search_query):

    if not search_query:

        return []

    search_text = (
        search_query
        .lower()
        .strip()
    )

    product_name = (
        products_df["ProductName"]
        .astype(str)
        .str.lower()
    )

    category = (
        products_df["Category"]
        .astype(str)
        .str.lower()
    )

    product_id = (
        products_df["ProductID"]
        .astype(str)
        .str.lower()
    )

    matched_products = (
        products_df[
            product_name.str.contains(
                search_text,
                na=False
            )
            |
            category.str.contains(
                search_text,
                na=False
            )
            |
            product_id.str.contains(
                search_text,
                na=False
            )
        ]
    )

    return (
        matched_products["ProductID"]
        .astype(str)
        .str.strip()
        .tolist()
    )


# ============================================================
# RECOMMENDATION ENGINE
# ============================================================

def get_recommendations(
    search_products=None
):

    recommendations = []

    purchased_products = (
        get_customer_purchases()
    )

    cart_products = (
        get_cart_products()
    )

    if search_products is None:

        search_products = []

    search_products = set(
        str(item).strip()
        for item in search_products
    )

    # --------------------------------------------------------
    # ACTIVE PRODUCTS
    # --------------------------------------------------------
    # Products influencing the recommendation:
    #
    # 1. Products already purchased
    # 2. Products currently in cart
    # 3. Products from the current search
    #
    # --------------------------------------------------------

    active_products = set()

    active_products.update(
        purchased_products
    )

    active_products.update(
        cart_products
    )

    active_products.update(
        search_products
    )

    if not active_products:

        return recommendations


    # ========================================================
    # LOAD FP-GROWTH ASSOCIATION RULES
    # ========================================================

    if not os.path.exists(
        RULES_FILE
    ):

        return recommendations

    try:

        rules_df = pd.read_csv(
            RULES_FILE
        )

    except Exception:

        return recommendations

    if rules_df.empty:

        return recommendations


    required_columns = [
        "antecedent",
        "consequent",
        "confidence",
        "lift"
    ]

    for column in required_columns:

        if column not in rules_df.columns:

            return recommendations


    # ========================================================
    # CLEAN ASSOCIATION RULES
    # ========================================================

    rules_df["antecedent"] = (
        rules_df["antecedent"]
        .astype(str)
        .str.replace(
            '"',
            "",
            regex=False
        )
        .str.replace(
            "[",
            "",
            regex=False
        )
        .str.replace(
            "]",
            "",
            regex=False
        )
        .str.strip()
    )

    rules_df["consequent"] = (
        rules_df["consequent"]
        .astype(str)
        .str.replace(
            '"',
            "",
            regex=False
        )
        .str.replace(
            "[",
            "",
            regex=False
        )
        .str.replace(
            "]",
            "",
            regex=False
        )
        .str.strip()
    )

    rules_df["confidence"] = pd.to_numeric(
        rules_df["confidence"],
        errors="coerce"
    )

    rules_df["lift"] = pd.to_numeric(
        rules_df["lift"],
        errors="coerce"
    )

    rules_df = rules_df.dropna(
        subset=[
            "confidence",
            "lift"
        ]
    )


    # ========================================================
    # SORT RULES
    # ========================================================

    rules_df = rules_df.sort_values(
        by=[
            "confidence",
            "lift"
        ],
        ascending=[
            False,
            False
        ]
    )


    # ========================================================
    # PROCESS FP-GROWTH RULES
    # ========================================================

    for _, rule in rules_df.iterrows():

        antecedent_products = set(
            item.strip()
            for item in
            str(
                rule["antecedent"]
            ).split(",")

            if item.strip()
        )


        # ----------------------------------------------------
        # CHECK CART + SEARCH
        # ----------------------------------------------------

        cart_match = (
            antecedent_products
            .issubset(
                active_products
            )
        )


        search_match = False

        if search_products:

            search_match = bool(
                antecedent_products
                .intersection(
                    search_products
                )
            )


        if not cart_match and not search_match:

            continue


        # ----------------------------------------------------
        # CONSEQUENT PRODUCTS
        # ----------------------------------------------------

        consequent_products = [
            item.strip()

            for item in
            str(
                rule["consequent"]
            ).split(",")

            if item.strip()
        ]


        for product_id in consequent_products:


            # ------------------------------------------------
            # NEVER RECOMMEND ACTIVE PRODUCT
            # ------------------------------------------------

            if product_id in active_products:

                continue


            # ------------------------------------------------
            # AVOID DUPLICATES
            # ------------------------------------------------

            already_exists = any(

                str(
                    item["ProductID"]
                )
                ==
                product_id

                for item in recommendations

            )

            if already_exists:

                continue


            # ------------------------------------------------
            # FIND PRODUCT
            # ------------------------------------------------

            matching_product = (
                products_df[
                    products_df["ProductID"]
                    ==
                    product_id
                ]
            )

            if matching_product.empty:

                continue


            product = (
                matching_product
                .iloc[0]
            )


            # ------------------------------------------------
            # ADD RECOMMENDATION
            # ------------------------------------------------

            recommendations.append({

                "ProductID":
                    product["ProductID"],

                "ProductName":
                    product["ProductName"],

                "Category":
                    product["Category"],

                "Price":
                    product["Price"],

                "Image":
                    get_product_image(
                        product["ProductName"]
                    ),

                "Confidence":
                    round(
                        float(
                            rule["confidence"]
                        ) * 100,
                        2
                    ),

                "Lift":
                    round(
                        float(
                            rule["lift"]
                        ),
                        2
                    ),

                "Antecedent":
                    rule["antecedent"],

                "Consequent":
                    rule["consequent"]

            })


            if len(
                recommendations
            ) >= 8:

                return recommendations


    # ========================================================
    # CATEGORY FALLBACK
    # ========================================================
    #
    # If FP-Growth does not find enough rules,
    # show products from the same category.
    #
    # This keeps the demo visually useful.
    #
    # ========================================================

    seed_ids = set(
        active_products
    )

    seed_categories = set(
        products_df[
            products_df["ProductID"]
            .isin(seed_ids)
        ]["Category"]
        .astype(str)
        .tolist()
    )


    if seed_categories:

        category_products = (
            products_df[
                products_df["Category"]
                .isin(
                    seed_categories
                )
            ]
        )


        for _, product in (
            category_products.iterrows()
        ):

            product_id = str(
                product["ProductID"]
            )


            if product_id in active_products:

                continue


            if any(
                str(
                    item["ProductID"]
                )
                ==
                product_id

                for item in recommendations
            ):

                continue


            recommendations.append({

                "ProductID":
                    product["ProductID"],

                "ProductName":
                    product["ProductName"],

                "Category":
                    product["Category"],

                "Price":
                    product["Price"],

                "Image":
                    get_product_image(
                        product["ProductName"]
                    ),

                "Confidence":
                    "Related",

                "Lift":
                    "-",

                "Antecedent":
                    "Related category",

                "Consequent":
                    product["ProductName"]

            })


            if len(
                recommendations
            ) >= 8:

                break


    return recommendations


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    search_query = request.args.get(
        "search",
        ""
    ).strip()


    # ========================================================
    # SEARCH
    # ========================================================

    display_products = (
        products_df.copy()
    )


    if search_query:

        search_text = (
            search_query
            .lower()
        )


        product_name = (
            display_products[
                "ProductName"
            ]
            .astype(str)
            .str.lower()
        )


        category = (
            display_products[
                "Category"
            ]
            .astype(str)
            .str.lower()
        )


        product_id = (
            display_products[
                "ProductID"
            ]
            .astype(str)
            .str.lower()
        )


        display_products = (
            display_products[
                product_name.str.contains(
                    search_text,
                    na=False
                )
                |
                category.str.contains(
                    search_text,
                    na=False
                )
                |
                product_id.str.contains(
                    search_text,
                    na=False
                )
            ]
        )


        # ----------------------------------------------------
        # SAVE SEARCH IN SESSION
        # ----------------------------------------------------

        session[
            "last_search"
        ] = search_query

        session[
            "last_search_products"
        ] = (
            display_products[
                "ProductID"
            ]
            .astype(str)
            .tolist()
        )

        session.modified = True


    else:

        # ----------------------------------------------------
        # USE LAST SEARCH AFTER ADD TO CART
        # ----------------------------------------------------

        last_search_products = (
            session.get(
                "last_search_products",
                []
            )
        )


        if last_search_products:

            search_product_set = set(
                str(item)
                for item in
                last_search_products
            )

        else:

            search_product_set = set()


    # ========================================================
    # PREPARE PRODUCT CARDS
    # ========================================================

    products = []


    for _, product in (
        display_products.iterrows()
    ):

        product_data = (
            product.to_dict()
        )


        product_data["Image"] = (
            get_product_image(
                product_data[
                    "ProductName"
                ]
            )
        )


        products.append(
            product_data
        )


    # ========================================================
    # CART
    # ========================================================

    cart = session.get(
        "cart",
        []
    )


    # ========================================================
    # SEARCH SEEDS
    # ========================================================

    if search_query:

        search_seed_products = (
            display_products[
                "ProductID"
            ]
            .astype(str)
            .tolist()
        )

    else:

        search_seed_products = (
            session.get(
                "last_search_products",
                []
            )
        )


    # ========================================================
    # RECOMMENDATIONS
    # ========================================================

    recommendations = (
        get_recommendations(
            search_seed_products
        )
    )


    # ========================================================
    # DISPLAY
    # ========================================================

    return render_template(

        "index.html",

        products=products,

        recommendations=
            recommendations,

        cart_count=
            len(cart),

        search_query=
            search_query

    )


# ============================================================
# PRODUCT DETAILS
# ============================================================

@app.route(
    "/product/<product_id>"
)
def product_details(
    product_id
):

    product_id = str(
        product_id
    ).strip()


    product_match = (
        products_df[
            products_df["ProductID"]
            ==
            product_id
        ]
    )


    if product_match.empty:

        return redirect(
            url_for("home")
        )


    product = (
        product_match
        .iloc[0]
        .to_dict()
    )


    product["Image"] = (
        get_product_image(
            product["ProductName"]
        )
    )


    cart = session.get(
        "cart",
        []
    )


    return render_template(

        "product_details.html",

        product=product,

        cart_count=
            len(cart)

    )


# ============================================================
# ADD TO CART
# ============================================================

@app.route(
    "/add_to_cart/<product_id>"
)
def add_to_cart(
    product_id
):

    cart = session.get(
        "cart",
        []
    )


    cart = [
        str(item)
        for item in cart
    ]


    product_id = str(
        product_id
    ).strip()


    # ========================================================
    # CHECK PRODUCT
    # ========================================================

    valid_product = (
        product_id
        in products_df[
            "ProductID"
        ].values
    )


    if not valid_product:

        return redirect(
            url_for("home")
        )


    # ========================================================
    # ADD ONLY ONCE
    # ========================================================

    if product_id not in cart:

        cart.append(
            product_id
        )


    session["cart"] = cart

    session.modified = True


    # ========================================================
    # RETURN TO HOME
    # KEEP SEARCH CONTEXT
    # ========================================================

    return redirect(
        url_for("home")
        + "#recommendations"
    )


# ============================================================
# REMOVE FROM CART
# ============================================================

@app.route(
    "/remove_from_cart/<product_id>"
)
def remove_from_cart(
    product_id
):

    cart = session.get(
        "cart",
        []
    )


    product_id = str(
        product_id
    ).strip()


    cart = [

        str(item)

        for item in cart

        if str(item)
        != product_id

    ]


    session["cart"] = cart

    session.modified = True


    return redirect(
        url_for("cart")
    )


# ============================================================
# CLEAR CART
# ============================================================

@app.route(
    "/clear_cart"
)
def clear_cart():

    session["cart"] = []

    session.modified = True


    return redirect(
        url_for("cart")
    )


# ============================================================
# CART PAGE
# ============================================================

@app.route(
    "/cart"
)
def cart():

    cart = session.get(
        "cart",
        []
    )


    cart = [
        str(item)
        for item in cart
    ]


    selected_products = (

        products_df[
            products_df["ProductID"]
            .isin(cart)
        ]

        .to_dict("records")

    )


    for product in selected_products:

        product["Image"] = (
            get_product_image(
                product["ProductName"]
            )
        )


    total = sum(

        float(
            product["Price"]
        )

        for product
        in selected_products

    )


    return render_template(

        "cart.html",

        products=
            selected_products,

        total=
            total,

        cart_count=
            len(cart)

    )


# ============================================================
# PURCHASE
# ============================================================

@app.route(
    "/purchase"
)
def purchase():

    cart = session.get(
        "cart",
        []
    )


    if not cart:

        return redirect(
            url_for("home")
        )


    cart = [
        str(item)
        for item in cart
    ]


    # ========================================================
    # TRANSACTION DETAILS
    # ========================================================

    transaction_id = (
        "T"
        +
        uuid.uuid4()
        .hex[:8]
        .upper()
    )


    purchase_date = (
        datetime.now()
        .strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    # ========================================================
    # GET PRODUCTS
    # ========================================================

    selected_products = (

        products_df[
            products_df["ProductID"]
            .isin(cart)
        ]

    )


    transactions = []


    for _, product in (
        selected_products.iterrows()
    ):

        transactions.append({

            "TransactionID":
                transaction_id,

            "CustomerID":
                CUSTOMER_ID,

            "ProductID":
                product["ProductID"],

            "ProductName":
                product["ProductName"],

            "Category":
                product["Category"],

            "Price":
                product["Price"],

            "Quantity":
                1,

            "PurchaseDate":
                purchase_date

        })


    # ========================================================
    # SAVE TRANSACTION
    # ========================================================

    new_transactions = (
        pd.DataFrame(
            transactions
        )
    )


    if os.path.exists(
        TRANSACTION_FILE
    ):

        new_transactions.to_csv(

            TRANSACTION_FILE,

            mode="a",

            header=False,

            index=False

        )

    else:

        new_transactions.to_csv(

            TRANSACTION_FILE,

            index=False

        )


    # ========================================================
    # TOTAL
    # ========================================================

    total = sum(

        float(
            product["Price"]
        )

        for product
        in selected_products
        .to_dict("records")

    )


    # ========================================================
    # CLEAR CART
    # ========================================================

    session["cart"] = []

    session.modified = True


    # ========================================================
    # ORDER SUCCESS
    # ========================================================

    return render_template(

        "order_success.html",

        transaction_id=
            transaction_id,

        total=
            total,

        products=
            selected_products
            .to_dict("records")

    )


# ============================================================
# MY ORDERS
# ============================================================

@app.route(
    "/orders"
)
def orders():

    orders = []


    if os.path.exists(
        TRANSACTION_FILE
    ):

        try:

            orders_df = pd.read_csv(
                TRANSACTION_FILE
            )


            if not orders_df.empty:

                customer_orders = (

                    orders_df[

                        orders_df[
                            "CustomerID"
                        ]
                        .astype(str)
                        .str.strip()
                        ==
                        CUSTOMER_ID

                    ]

                )


                orders = (
                    customer_orders
                    .to_dict(
                        "records"
                    )
                )


        except Exception:

            orders = []


    return render_template(

        "orders.html",

        orders=orders

    )


# ============================================================
# RECOMMENDATION DASHBOARD
# ============================================================

@app.route(
    "/recommendation_dashboard"
)
def recommendation_dashboard():

    rules = []

    total_rules = 0

    average_confidence = 0

    average_lift = 0


    # ========================================================
    # LOAD ASSOCIATION RULES
    # ========================================================

    if os.path.exists(
        RULES_FILE
    ):

        try:

            rules_df = pd.read_csv(
                RULES_FILE
            )

        except Exception:

            rules_df = (
                pd.DataFrame()
            )


        if not rules_df.empty:

            if (
                "confidence"
                in rules_df.columns
            ):

                rules_df[
                    "confidence"
                ] = pd.to_numeric(

                    rules_df[
                        "confidence"
                    ],

                    errors="coerce"

                )


            if (
                "lift"
                in rules_df.columns
            ):

                rules_df[
                    "lift"
                ] = pd.to_numeric(

                    rules_df[
                        "lift"
                    ],

                    errors="coerce"

                )


            rules_df = (
                rules_df.dropna(
                    subset=[
                        "confidence",
                        "lift"
                    ]
                )
            )


            total_rules = len(
                rules_df
            )


            if total_rules > 0:

                average_confidence = round(

                    rules_df[
                        "confidence"
                    ]
                    .mean()
                    * 100,

                    2

                )


                average_lift = round(

                    rules_df[
                        "lift"
                    ]
                    .mean(),

                    2

                )


                rules = (
                    rules_df
                    .to_dict(
                        "records"
                    )
                )


    # ========================================================
    # OTHER STATISTICS
    # ========================================================

    total_products = len(
        products_df
    )


    purchased_products = len(
        get_customer_purchases()
    )


    recommendations = (
        get_recommendations()
    )


    recommendation_count = len(
        recommendations
    )


    # ========================================================
    # RENDER
    # ========================================================

    return render_template(

        "recommendation_dashboard.html",

        rules=rules,

        total_rules=
            total_rules,

        average_confidence=
            average_confidence,

        average_lift=
            average_lift,

        total_products=
            total_products,

        purchased_products=
            purchased_products,

        recommendation_count=
            recommendation_count,

        recommendations=
            recommendations

    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )