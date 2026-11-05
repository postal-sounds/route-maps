#!/usr/bin/env python3
"""Guarda una copia estática de los datos de Supabase para los mapas.

Los mapas la usan si Supabase no responde. Usa la clave publicable, de solo
lectura. Si llegan muchas menos filas que en la copia anterior, no escribe nada.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SUPABASE_URL = "https://jwwwekafkpjdtngtjzfe.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_ypy8gKygTS_JJSin3HVdyQ_-aJWXvtc"
PAGE_SIZE = 1000
MIN_ROWS_RATIO = 0.5

SPOT_COLUMNS = (
    "id,city,name,name_en,description,description_en,category,access_type,"
    "latitude,longitude,image_url,embed_html,genre_primary,decade,vibe,extra,extra_en,url_extra,"
    "spot_events(description,description_en,url,position)"
)
ROUTE_COLUMNS = "id,name,description,description_en"
STOP_COLUMNS = (
    "id,route_id,position,name,name_en,description,description_en,access_type,"
    "latitude,longitude,image_url,embed_html,videos,extra_text,comments"
)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def fetch_table(table, columns, order):
    rows = []
    while True:
        query = urllib.parse.urlencode({
            "select": columns,
            "order": order,
            "limit": PAGE_SIZE,
            "offset": len(rows),
        })
        request = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{table}?{query}",
            headers={"apikey": SUPABASE_PUBLISHABLE_KEY, "User-Agent": "postal-sounds-snapshot"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            page = json.load(response)
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows


def previous_count(path, count_rows):
    if not path.exists():
        return 0
    return count_rows(json.loads(path.read_text(encoding="utf-8")))


def write_json(path, data):
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8")


def main():
    spots = fetch_table("spots", SPOT_COLUMNS, "id")
    routes = fetch_table("routes", ROUTE_COLUMNS, "id")
    stops = fetch_table("route_stops", STOP_COLUMNS, "route_id,position")
    route_data = {"routes": routes, "stops": stops}

    spots_path = DATA_DIR / "spots.json"
    routes_path = DATA_DIR / "routes.json"
    checks = [
        ("spots", len(spots), previous_count(spots_path, len)),
        ("routes", len(routes), previous_count(routes_path, lambda d: len(d["routes"]))),
        ("route_stops", len(stops), previous_count(routes_path, lambda d: len(d["stops"]))),
    ]
    for name, count, previous in checks:
        if count == 0 or count < previous * MIN_ROWS_RATIO:
            sys.exit(f"{name}: {count} filas frente a {previous}; no se escribe la copia")

    DATA_DIR.mkdir(exist_ok=True)
    write_json(spots_path, spots)
    write_json(routes_path, route_data)
    print(f"spots={len(spots)} routes={len(routes)} route_stops={len(stops)}")


if __name__ == "__main__":
    main()
