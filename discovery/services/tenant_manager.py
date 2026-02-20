import os
import sqlite3
import json
from django.conf import settings


class TenantDatabaseManager:
    @staticmethod
    def get_db_path(tenant_slug):
        os.makedirs(settings.TENANT_DB_ROOT, exist_ok=True)
        return os.path.join(settings.TENANT_DB_ROOT, f"{tenant_slug}.db")

    @classmethod
    def initialize_tenant_db(cls, tenant_slug):
        db_path = cls.get_db_path(tenant_slug)
        if os.path.exists(db_path):
            return

        with open(settings.SQL_TEMPLATE_PATH, "r") as f:
            schema_sql = f.read()

        conn = sqlite3.connect(db_path)
        try:
            # Split by semicolon and execute (simple parser)
            statements = schema_sql.split(";")
            for stmt in statements:
                if stmt.strip():
                    conn.execute(stmt)
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def apply_action(cls, tenant_slug, action_type, payload):
        db_path = cls.get_db_path(tenant_slug)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            if action_type == "UPSERT_PRODUCT":
                p = payload.get("product")
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO products (id, name, category, manufacturer, barcode, price, tax, tax_is_flat_rate, quantity, image_path, section, shelf)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        p["id"],
                        p["name"],
                        p["category"],
                        p.get("manufacturer"),
                        p.get("barcode"),
                        p["price"],
                        p.get("tax", 0),
                        1 if p.get("isTaxFlatRate") else 0,
                        p["quantity"],
                        p.get("imagePath"),
                        p.get("section"),
                        p.get("shelf"),
                    ),
                )

            elif action_type == "ADD_STOCK":
                s = payload.get("stock")
                cursor.execute(
                    """
                    INSERT INTO stocks (product_id, supplier, supplier_contact, unit_price, purchase_price, purchase_date, expiry_date, quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        s["productId"],
                        s.get("supplier"),
                        s.get("supplierContact"),
                        s["unitPrice"],
                        s["purchasePrice"],
                        s.get("purchaseDate"),
                        s.get("expiryDate"),
                        s["quantity"],
                    ),
                )

                # Derivative update for product quantity
                cursor.execute(
                    "UPDATE products SET quantity = quantity + ? WHERE id = ?",
                    (s["quantity"], s["productId"]),
                )

            elif action_type == "RECORD_SALE":
                cart = payload.get("cart")
                customer_id = payload.get("customerId")

                # Insert Sale
                cursor.execute(
                    """
                    INSERT INTO sales (customer_id, subtotal, tax, discount, total, paid_amount, change_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        customer_id,
                        cart["subtotal"],
                        cart["tax"],
                        cart["discount"],
                        cart["total"],
                        cart.get("paidAmount", cart["total"]),
                        cart.get("changeAmount", 0),
                    ),
                )
                sale_id = cursor.lastrowid

                # Insert Items and Decrement Stock
                for item in cart["items"]:
                    cursor.execute(
                        """
                        INSERT INTO sale_items (sale_id, product_id, quantity, price)
                        VALUES (?, ?, ?, ?)
                    """,
                        (sale_id, item["productId"], item["quantity"], item["price"]),
                    )
                    cursor.execute(
                        "UPDATE products SET quantity = quantity - ? WHERE id = ?",
                        (item["quantity"], item["productId"]),
                    )

            elif action_type == "UPSERT_CUSTOMER":
                c = payload
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO customers (id, name, contact, payment_method)
                    VALUES (?, ?, ?, ?)
                """,
                    (c["id"], c.get("name"), c.get("contact"), c.get("paymentMethod")),
                )

            elif action_type == "DELETE_PRODUCT":
                cursor.execute(
                    "UPDATE products SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (payload.get("id"),),
                )

            elif action_type == "RESTORE_PRODUCT":
                cursor.execute(
                    "UPDATE products SET deleted_at = NULL WHERE id = ?",
                    (payload.get("id"),),
                )

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
