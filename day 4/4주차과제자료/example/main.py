import json
import os
import logging
import functions_framework
import google.auth

from datetime import datetime, date
from flask import jsonify, Request
from google.cloud import bigquery
from google.api_core import exceptions as gexc


def parse_iso_date(value: str) -> datetime.date:
    """Parse a date string in YYYY-MM-DD format and return a date object."""
    return datetime.strptime(value, "%Y-%m-%d").date()


@functions_framework.http
def hello_http(request: Request):
    # /orders/summary 엔드포인트만 처리
    if request.path == "/orders/summary":
        try:
            # GCP 프로젝트 ID 가져오기
            _, project = google.auth.default()
            dataset = "assignment_data"

            # start_date / end_date 파라미터 받기
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")
            if not start_date or not end_date:
                return jsonify({"error": "start_date and end_date query parameters are required"}), 400

            # 문자열 → DATE 객체 변환
            start_dt = parse_iso_date(start_date)
            end_dt = parse_iso_date(end_date)

            # BigQuery Client 생성
            client = bigquery.Client(project=project)

            # ✅ SQL에서 집계
            query = """
                SELECT 
                    COUNT(order_id) AS total_orders,
                    SUM(amount) AS total_amount,
                    AVG(amount) AS average_amount
                FROM `gcp-camp-466802.assignment_data.orders`
                WHERE order_date BETWEEN @start_date AND @end_date
            """

            # DATE 파라미터 바인딩
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("start_date", "DATE", start_dt),
                    bigquery.ScalarQueryParameter("end_date", "DATE", end_dt)
                ]
            )

            # 쿼리 실행
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())

            # 집계 결과는 한 줄만 나옴
            if results:
                row = results[0]
                response = {
                    "total_orders": row.total_orders,
                    "total_amount": float(row.total_amount) if row.total_amount else 0,
                    "average_amount": float(row.average_amount) if row.average_amount else 0
                }
            else:
                response = {
                    "total_orders": 0,
                    "total_amount": 0,
                    "average_amount": 0
                }

            return jsonify(response)

        except gexc.Forbidden as e:
            logging.exception("BigQuery permission error")
            return jsonify({"error": "BigQuery permission error", "detail": str(e)}), 403
        except Exception as e:
            logging.exception("Unhandled error")
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Unsupported request"}), 400
