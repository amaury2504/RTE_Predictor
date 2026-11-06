"""Génère `src/lib/franceRegions.ts` : les contours des 13 régions métropolitaines, prêts à dessiner en SVG.

Source : contours simplifiés des régions (IGN Admin Express) publiés par le dépôt ouvert
`gregoiredavid/france-geojson`, sous Licence Ouverte Etalab 2.0 (attribution requise).

Usage (depuis `frontend/`) :   python scripts/generate_france_regions.py
Dépendances : bibliothèque standard seulement. Le résultat est versionné : ce script ne sert qu'à le régénérer.
"""
import json
import math
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson"
OUT = Path(__file__).resolve().parent.parent / "src" / "lib" / "franceRegions.ts"

# Projection équirectangulaire corrigée de la latitude (même repère que le reste de l'application)
LAT_MAX, LON_MIN, SCALE = 51.2, -5.2, 40
LON_FACTOR = math.cos(math.radians(46))
TOLERANCE = 0.4  # unités du dessin (~1 km) : lisse les micro-détails sans déformer les frontières


def project(lon: float, lat: float) -> tuple[float, float]:
    return (lon - LON_MIN) * LON_FACTOR * SCALE, (LAT_MAX - lat) * SCALE


def simplify(points: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    """Douglas-Peucker (version itérative)."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = points[a], points[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-12
        far, far_d = -1, 0.0
        for i in range(a + 1, b):
            px, py = points[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > far_d:
                far, far_d = i, d
        if far_d > tol:
            keep[far] = True
            stack += [(a, far), (far, b)]
    return [p for p, k in zip(points, keep) if k]


def ring_to_path(ring: list[list[float]]) -> str:
    raw = [project(lon, lat) for lon, lat in ring]
    # Un contour fermé a le même début et la même fin : on le coupe en deux moitiés avant de simplifier
    mid = len(raw) // 2
    pts = simplify(raw[: mid + 1], TOLERANCE)[:-1] + simplify(raw[mid:], TOLERANCE)
    if len(pts) < 4:
        return ""
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"


def main() -> None:
    with urllib.request.urlopen(URL, timeout=30) as response:
        data = json.load(response)

    regions = []
    for feature in data["features"]:
        geometry = feature["geometry"]
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        paths, ys = [], []
        for polygon in polygons:
            for ring in polygon:  # anneau extérieur, puis trous éventuels
                path = ring_to_path(ring)
                if path:
                    paths.append(path)
            ys += [project(lon, lat)[1] for lon, lat in polygon[0]]
        regions.append({"name": feature["properties"]["nom"], "d": " ".join(paths), "cy": round((min(ys) + max(ys)) / 2, 1)})

    regions.sort(key=lambda r: r["cy"])
    width = round((9.9 - LON_MIN) * LON_FACTOR * SCALE)
    height = round((LAT_MAX - 41.2) * SCALE)

    lines = [
        "// Fichier généré par scripts/generate_france_regions.py : ne pas modifier à la main.",
        "// Contours : IGN Admin Express (simplifiés), via gregoiredavid/france-geojson. Licence Ouverte Etalab 2.0.",
        "",
        f"export const FRANCE_WIDTH = {width}",
        f"export const FRANCE_HEIGHT = {height}",
        "",
        "/** Les 13 régions métropolitaines, du nord au sud. `cy` : hauteur du centre de la région dans le dessin. */",
        "export const FRANCE_REGIONS: { name: string; d: string; cy: number }[] = [",
    ]
    for r in regions:
        lines.append(f"    {{ name: {json.dumps(r['name'], ensure_ascii=False)}, cy: {r['cy']}, d: {json.dumps(r['d'])} }},")
    lines.append("]")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    total = sum(len(r["d"]) for r in regions)
    print(f"{len(regions)} régions, {total / 1024:.0f} Ko de tracés -> {OUT}")


if __name__ == "__main__":
    main()
