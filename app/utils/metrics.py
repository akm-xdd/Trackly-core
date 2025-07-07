from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from functools import wraps

# Define metrics
ISSUE_COUNTER = Counter(
    'trackly_issues_total', 
    'Total issues created', 
    ['severity', 'user_role']
)

LOGIN_COUNTER = Counter(
    'trackly_logins_total', 
    'Total login attempts', 
    ['status', 'method']
)

API_REQUEST_DURATION = Histogram(
    'trackly_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint', 'status_code']
)

ISSUES_GAUGE = Gauge(
    'trackly_all_issues',
    'All issues',
    ['severity']
)

# Convenience functions
def track_issue_created(severity: str, user_role: str):
    """Track when an issue is created"""
    ISSUE_COUNTER.labels(severity=severity, user_role=user_role).inc()

def track_login_attempt(success: bool, method: str = 'password'):
    """Track login attempts"""
    status = 'success' if success else 'failed'
    LOGIN_COUNTER.labels(status=status, method=method).inc()

def track_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Track API request metrics"""
    API_REQUEST_DURATION.labels(
        method=method, 
        endpoint=endpoint, 
        status_code=str(status_code)
    ).observe(duration)

def update_all_issues_gauge(severity_counts: dict):
    """Update the all issues gauge"""
    for severity, count in severity_counts.items():
        ISSUES_GAUGE.labels(severity=severity).set(count)

# Decorator for timing API requests
def track_request_time(endpoint_name: str):
    """Decorator to track request duration"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status_code = getattr(result, 'status_code', 200)
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                track_api_request('POST', endpoint_name, status_code, duration)
        return wrapper
    return decorator

def get_metrics():
    """Get Prometheus metrics in text format"""
    return generate_latest()

def get_metrics_content_type():
    """Get the content type for Prometheus metrics"""
    return CONTENT_TYPE_LATEST