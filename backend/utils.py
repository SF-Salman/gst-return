def safe_float(value) -> float:
    try:
        return round(float(value), 2) if value and value != "-" else 0.0
    except (ValueError, TypeError):
        return 0.0

def safe_get(data: dict, *keys):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data