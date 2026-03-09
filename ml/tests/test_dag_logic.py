"""Airflow DAG의 데이터 수집 로직 단위 테스트"""

import sys
import os
from unittest.mock import patch, MagicMock

import pytest

# DAG 모듈 로드를 위한 경로 설정
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "airflow", "dags")
)


class TestFetchSingleDraw:
    """fetch_single_draw 함수 테스트"""

    @patch("lotto_collect_dag.requests.get")
    def test_success(self, mock_get):
        from lotto_collect_dag import fetch_single_draw

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "returnValue": "success",
            "drwNo": 1,
            "drwNoDate": "2002-12-07",
            "drwtNo1": 10, "drwtNo2": 23, "drwtNo3": 29,
            "drwtNo4": 33, "drwtNo5": 37, "drwtNo6": 40,
            "bnusNo": 16,
            "totSellamnt": 3681782000,
            "firstWinamnt": 0,
            "firstPrzwnerCo": 0,
            "firstAccumamnt": 863604600,
        }

        result = fetch_single_draw(1)
        assert result is not None
        assert result["drwNo"] == 1
        assert result["numbers"] == [10, 23, 29, 33, 37, 40]
        assert result["bonusNo"] == 16
        assert len(result["numbers"]) == 6
        # 번호가 정렬되어 있는지
        assert result["numbers"] == sorted(result["numbers"])

    @patch("lotto_collect_dag.requests.get")
    def test_fail_return(self, mock_get):
        from lotto_collect_dag import fetch_single_draw

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"returnValue": "fail"}

        result = fetch_single_draw(9999)
        assert result is None

    @patch("lotto_collect_dag.requests.get")
    def test_network_error(self, mock_get):
        from lotto_collect_dag import fetch_single_draw

        mock_get.side_effect = Exception("Connection error")

        result = fetch_single_draw(1)
        assert result is None
