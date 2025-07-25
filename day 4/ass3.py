import json
import os
import logging
import functions_framework
import google.auth

from datetime import datetime, date
from flask import jsonify, Request
from google.cloud import bigquery
from google.api_core import exceptions as gexc


@functions_framework.http
def hello_http(request):
    # /orders/detail 엔드포인트
    if request.path == "/orders/detail":
        try:
            # order_id 파라미터 필수
            order_id_param = request.args.get("order_id")
            if not order_id_param:
                return jsonify({"error": "order_id query parameter is required"}), 400

            try:
                order_id = int(order_id_param)
            except ValueError:
                return jsonify({"error": "order_id must be an integer"}), 400

            # GCP 인증
            _, project = google.auth.default()
            client = bigquery.Client(project=project)

            # 단일 주문 조회 쿼리
            query = """
                SELECT 
                  o.order_id,
                  o.order_date,
                  c.customer_id,
                  c.name AS customer_name,
                  c.city,
                  p.product_id,
                  p.product_name,
                  p.category,
                  oi.quantity,
                  p.price AS unit_price,
                  (oi.quantity * p.price) AS total_price
                FROM `gcp-camp-466802.assignment_data.orders` o
                JOIN `gcp-camp-466802.assignment_data.customers` c 
                  ON o.customer_id = CAST(c.customer_id AS INT64)
                JOIN `gcp-camp-466802.assignment_data.order_items` oi 
                  ON o.order_id = CAST(oi.order_id AS INT64)
                JOIN `gcp-camp-466802.assignment_data.products` p 
                  ON oi.product_id = CAST(p.product_id AS INT64)
                WHERE o.order_id = @order_id
                ORDER BY p.product_id
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("order_id", "INT64", order_id)
                ]
            )

            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())

            # 주문이 없으면 404 반환
            if not results:
                return jsonify({"error": f"Order {order_id} not found"}), 404

            # 첫 row에서 주문 및 고객 정보 추출
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

            # 항목 추가
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

        except Exception as e:
            logging.exception("Unhandled error")
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Unsupported request"}), 400
