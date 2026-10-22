from pathlib import Path
from config import RAW_DIR

def main() -> None:
    try:
        import osmnx as ox
    except ImportError as exc:
        raise RuntimeError("OSM download is optional. Install requirements-optional.txt first.") from exc
    out = RAW_DIR.parent / "reference" / "osm"
    out.mkdir(parents=True, exist_ok=True)
    graph_path = out / "manhattan_drive.graphml"
    if graph_path.exists():
        print(f"OSM graph already exists: {graph_path}")
        return
    graph = ox.graph_from_place("Manhattan, New York City, New York, USA", network_type="drive")
    ox.save_graphml(graph, graph_path)
    edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)
    edges.to_file(out / "manhattan_roads.geojson", driver="GeoJSON")
    print(f"OSM network saved: {out}")

if __name__ == "__main__":
    main()
