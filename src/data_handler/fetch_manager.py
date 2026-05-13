import os
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")


FetchError = Dict[str, Any]


def _build_column_suggestions(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    col_suggestions: Dict[str, Dict[str, Any]] = {}
    for col in df.columns:
        series = df[col]
        col_suggestions[col] = {
            "dtype": str(series.dtype),
            "num_unique": int(series.nunique(dropna=True)),
            "num_missing": int(series.isna().sum()),
            "sample_values": series.dropna().unique()[:5].tolist(),
        }
    return col_suggestions


def _redact_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        qs = parse_qsl(parts.query, keep_blank_values=True)
        redacted = []
        for k, v in qs:
            if k.lower() in {"api-key", "apikey", "api_key", "key"}:
                redacted.append((k, "***redacted***"))
            else:
                redacted.append((k, v))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(redacted), parts.fragment))
    except Exception:
        return url


def _request_json_with_retries(
    session: requests.Session,
    *,
    url: str,
    params: Dict[str, Any],
    timeout_s: int,
    max_retries: int,
    backoff_s: float,
) -> Tuple[Optional[Dict[str, Any]], Optional[FetchError]]:
    last_err: Optional[FetchError] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(
                url,
                params=params,
                timeout=timeout_s,
                headers={"Accept": "application/json", "User-Agent": "Project-Samarth/1.0 (+streamlit)"},
            )
            status = response.status_code

            # Retry transient errors / throttling
            if status in {429, 502, 503, 504}:
                last_err = {
                    "kind": "http_retryable_error",
                    "status_code": status,
                    "message": f"HTTP {status} from data.gov.in API (retryable)",
                    "url": _redact_url(response.url),
                    "attempt": attempt,
                    "max_retries": max_retries,
                }
                if attempt < max_retries:
                    time.sleep(backoff_s * (2 ** (attempt - 1)))
                    continue
                return None, last_err

            if status >= 400:
                text_preview = (response.text or "")[:500]
                err = {
                    "kind": "http_error",
                    "status_code": status,
                    "message": f"HTTP {status} from data.gov.in API",
                    "url": _redact_url(response.url),
                    "response_preview": text_preview,
                }
                return None, err

            return response.json(), None

        except (requests.Timeout, requests.ConnectionError) as e:
            last_err = {
                "kind": "network_timeout",
                "message": str(e),
                "url": _redact_url(url),
                "attempt": attempt,
                "max_retries": max_retries,
                "timeout_s": timeout_s,
            }
            if attempt < max_retries:
                time.sleep(backoff_s * (2 ** (attempt - 1)))
                continue
            return None, last_err
        except ValueError as e:
            return None, {"kind": "json_decode_error", "message": str(e), "url": _redact_url(url)}
        except Exception as e:
            return None, {"kind": "unknown_error", "message": str(e), "url": _redact_url(url)}

    return None, last_err or {"kind": "unknown_error", "message": "Unknown fetch failure", "url": _redact_url(url)}


def fetch_from_api(
    resource_id: str,
    limit: int = 1000,
    *,
    timeout_s: int = 60,
    max_retries: int = 3,
    backoff_s: float = 1.0,
) -> Tuple[pd.DataFrame, Dict[str, Any], Optional[FetchError]]:
    """
    Fetch data from data.gov.in API using resource_id.

    Returns:
      - df: pandas DataFrame (empty if fetch fails or no records)
      - col_suggestions: dict
      - error: structured error dict (None on success)
    """
    base_url = "https://api.data.gov.in/resource/"
    url = f"{base_url}{resource_id}"

    if not API_KEY:
        return (
            pd.DataFrame(),
            {},
            {
                "kind": "missing_api_key",
                "message": "API_KEY is missing. Add API_KEY to your .env file (repo root) and restart the app.",
            },
        )

    params = {"api-key": API_KEY, "format": "json", "limit": int(limit)}

    session = requests.Session()

    data, err = _request_json_with_retries(
        session, url=url, params=params, timeout_s=timeout_s, max_retries=max_retries, backoff_s=backoff_s
    )
    if err and err.get("kind") in {"http_retryable_error", "http_error"} and err.get("status_code") in {502, 503, 504}:
        # Fallback endpoint (seen in earlier experiments / docs)
        fallback_url = "https://data.gov.in/api/datastore/resource.json"
        fallback_params = {
            "resource_id": resource_id,
            "api-key": API_KEY,
            "format": "json",
            "limit": int(limit),
        }
        fb_data, fb_err = _request_json_with_retries(
            session,
            url=fallback_url,
            params=fallback_params,
            timeout_s=timeout_s,
            max_retries=max_retries,
            backoff_s=backoff_s,
        )
        if fb_data is not None and fb_err is None:
            data = fb_data
            err = None
        else:
            return pd.DataFrame(), {}, {
                "kind": "fallback_failed",
                "message": "Primary endpoint failed and fallback endpoint also failed.",
                "primary_error": err,
                "fallback_error": fb_err,
            }

    if err is not None:
        return pd.DataFrame(), {}, err

    records = data.get("records") if isinstance(data, dict) else None
    if isinstance(records, list):
        df = pd.DataFrame(records)
        return df, _build_column_suggestions(df), None

    return (
        pd.DataFrame(),
        {},
        {
            "kind": "unexpected_response_shape",
            "message": "JSON response did not contain a 'records' list.",
            "top_level_keys": list(data.keys())[:50] if isinstance(data, dict) else None,
        },
    )
