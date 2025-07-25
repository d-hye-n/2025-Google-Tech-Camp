
import logging
import functions_framework
import google.auth

from datetime import datetime
from flask import jsonify, Request
from google.cloud import bigquery
from google.api_core import exceptions as gexc

def parse_iso_date(value: str) -> datetime.date:
    """Parse a date string in YYYY-MM-DD format and return a date object."""
    return datetime.strptime(value, "%Y-%m-%d").date()

@functions_framework.http
def hello_http(request: Request):
    """
    HTTP Cloud Function that routes requests based on the path.
    - /customers: Fetches customer data by city.
    - /orders/summary: Provides a summary of orders within a date range.
    - /orders/detail: Fetches the details of a specific order.
    """
    try:
        # Initialize GCP and BigQuery clients
        _, project = google.auth.default()
        client = bigquery.Client(project=project)

        # --- Router: Route request based on path ---
        
        # Route for /orders/summary (from ass2.py)
        if request.path == "/orders/summary":
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")
            if not start_date or not end_date:
                return jsonify({"error": "start_date and end_date query parameters are required"}), 400

            start_dt = parse_iso_date(start_date)
            end_dt = parse_iso_date(end_date)

            query = """
                SELECT 
                    COUNT(order_id) AS total_orders,
                    SUM(amount) AS total_amount,
                    AVG(amount) AS average_amount
                FROM `gcp-camp-466802.assignment_data.orders`
                WHERE order_date BETWEEN @start_date AND @end_date
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("start_date", "DATE", start_dt),
                    bigquery.ScalarQueryParameter("end_date", "DATE", end_dt)
                ]
            )
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())

            if results:
                row = results[0]
                response = {
                    "total_orders": row.total_orders,
                    "total_amount": float(row.total_amount) if row.total_amount else 0,
                    "average_amount": float(row.average_amount) if row.average_amount else 0
                }
            else:
                response = {"total_orders": 0, "total_amount": 0, "average_amount": 0}
            
            return jsonify(response)

        # Route for /orders/detail (from ass3.py)
        elif request.path == "/orders/detail":
            order_id_param = request.args.get("order_id")
            if not order_id_param:
                return jsonify({"error": "order_id query parameter is required"}), 400
            try:
                order_id = int(order_id_param)
            except ValueError:
                return jsonify({"error": "order_id must be an integer"}), 400

            query = """
                SELECT 
                  o.order_id, o.order_date, c.customer_id, c.name AS customer_name, c.city,
                  p.product_id, p.product_name, p.category, oi.quantity, p.price AS unit_price,
                  (oi.quantity * p.price) AS total_price
                FROM `gcp-camp-466802.assignment_data.orders` o
                JOIN `gcp-camp-466802.assignment_data.customers` c ON o.customer_id = CAST(c.customer_id AS INT64)
                JOIN `gcp-camp-466802.assignment_data.order_items` oi ON o.order_id = CAST(oi.order_id AS INT64)
                JOIN `gcp-camp-466802.assignment_data.products` p ON oi.product_id = CAST(p.product_id AS INT64)
                WHERE o.order_id = @order_id
                ORDER BY p.product_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("order_id", "INT64", order_id)]
            )
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())

            if not results:
                return jsonify({"error": f"Order {order_id} not found"}), 404

            order_detail = {
                "order_id": results[0].order_id,
                "order_date": results[0].order_date.isoformat(),
                "customer": {
                    "customer_id": int(results[0].customer_id),
                    "name": results[0].customer_name,
                    "city": results[0].city
                },
                "items": [],
                "order_total": 0.0
            }
            total_sum = 0.0
            for row in results:
                order_detail["items"].append({
                    "product_id": row.product_id,
                    "product_name": row.product_name,
                    "category": row.category,
                    "quantity": row.quantity,
                    "unit_price": float(row.unit_price),
                    "total_price": float(row.total_price)
                })
                total_sum += float(row.total_price)
            order_detail["order_total"] = total_sum

            return jsonify(order_detail)

        # Default route for /customers (from ass1.py)
        else:
            city = request.args.get("city")
            if not city:
                return jsonify({"error": "city query parameter is required"}), 400

            query = """
                SELECT c.customer_id, c.name, c.city, c.signup_date
                FROM `gcp-camp-466802.assignment_data.customers` AS c
                WHERE c.city = @city
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("city", "STRING", city)]
            )
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())

            response = [
                {
                    "customer_id": int(row.customer_id),
                    "name": row.name,
                    "city": row.city,
                    "signup_date": row.signup_date.isoformat() if row.signup_date else None
                }
                for row in results
            ]
            return jsonify(response)

    except gexc.Forbidden as e:
        logging.exception("BigQuery permission error")
        return jsonify({"error": "BigQuery permission error", "detail": str(e)}), 403
    except Exception as e:
        logging.exception("Unhandled error")
        return jsonify({"error": str(e)}), 500
