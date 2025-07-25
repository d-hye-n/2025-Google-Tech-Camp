import json
import os
import functions_framework
import google.auth

from datetime import datetime, date
from typing import Any, Dict, List
from flask import abort, jsonify, Request
from google.cloud import bigquery
from google.api_core import exceptions as gexc

def parse_iso_date(value: str) -> datetime.date:
    """Parse a date string in YYYY-MM-DD format and return a date object.

    사용 예시:

    range_date = request.args.get("range_date")
    range_dt = parse_iso_date(range_date)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("range_date", "DATE", range_dt), <- Date 형 아니면 안됨
        ]
    )

    """
    return datetime.strptime(value, "%Y-%m-%d").date()

@functions_framework.http
def hello_http(request):
    try:

        # 프로젝트 ID 및 데이터세트 ID 환경변수 가져오기
        _, project = google.auth.default()
        dataset = "assignment_data"

        # (중요) 요청 파라미터 획득
        city = request.args.get("city")
        if not city:
            return jsonify({"error": "city query parameter is required"}), 400

        # bigquery Client 생성
        client = bigquery.Client(project=project)

        # (중요) SQL 쿼리문 작성
        query = """
            SELECT 
                c.customer_id, 
                c.name, 
                c.city, 
                c.signup_date
            FROM `gcp-camp-466802.assignment_data.customers` AS c
            WHERE c.city = @city
            """

        # (중요) SQL 의 @에 값 할당하는 부분
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("city", "STRING", city)]
        )

        # (중요) 쿼리 실행 및 결과 사용, list 형식으로 반환하게 처리
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())


        # (중요) 쿼리를 통해 획득한 결과값을 response 에 지정된 형식으로 담기
        response = [
        {
            "customer_id": int(row.customer_id),
            "name": row.name,
            "city": row.city,
            "signup_date": row.signup_date.isoformat() if row.signup_date else None
        }
        for row in results
    ]
 # or {}

        return jsonify(response)

    except gexc.Forbidden as e:
        logging.exception("BigQuery permission error")
        return jsonify({"error": "BigQuery permission error", "detail": str(e)}), 403
    except Exception as e:
        logging.exception("Unhandled error")
        return jsonify({"error": str(e)}), 500