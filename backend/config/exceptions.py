from rest_framework.views import exception_handler as drf_exception_handler


def _messages(data):
    if isinstance(data, str):
        return [data]
    if isinstance(data, list):
        found = []
        for item in data:
            found.extend(_messages(item))
        return found
    if isinstance(data, dict):
        found = []
        for value in data.values():
            found.extend(_messages(value))
        return found
    return []


def exception_handler(exc, context):
    """Put the first validation message on detail so the dashboard can show it."""
    response = drf_exception_handler(exc, context)
    if response is None or not isinstance(response.data, dict):
        return response
    detail = response.data.get("detail")
    if isinstance(detail, str) and detail:
        return response
    messages = _messages(response.data)
    if messages:
        response.data["detail"] = messages[0] if len(messages) == 1 else " ".join(messages)
    return response
