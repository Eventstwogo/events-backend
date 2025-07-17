from typing import Any, Dict


def assert_dict_contains(
    actual: Dict[str, Any], expected: Dict[str, Any]
) -> None:
    for k, v in expected.items():
        if k not in actual or actual[k] != v:
            raise AssertionError(f"Expected {k}={v}, got {actual.get(k)}")


def assert_response_success(
    resp: Dict[str, Any], expected_status: int = 200
) -> None:
    if resp["status_code"] != expected_status:
        raise AssertionError(
            f"Expected {expected_status}, got {resp['status_code']}"
        )
    if resp["data"] is None:
        raise AssertionError("Response should contain data")


def assert_response_error(
    resp: Dict[str, Any], expected_status: int = 400
) -> None:
    if resp["status_code"] != expected_status:
        raise AssertionError(
            f"Expected {expected_status}, got {resp['status_code']}"
        )
    if resp["data"] and not (
        "detail" in resp["data"] or "message" in resp["data"]
    ):
        raise AssertionError("Error response should contain detail or message")
