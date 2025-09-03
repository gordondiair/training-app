def hhmmss_to_seconds(txt: str) -> int:
    """'HH:MM:SS' -> secondes"""
    h, m, s = [int(x) for x in txt.split(":")]
    return h*3600 + m*60 + s

def seconds_to_excel_time(seconds: int) -> float:
    """Convertit des secondes en valeur temps Excel (jours)"""
    return (seconds or 0) / 86400.0
