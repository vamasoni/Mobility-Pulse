"""Run source extractors in dependency order. Large historical downloads can take time."""
from ingestion import reference, dot, tlc, weather, collisions

def main() -> None:
    for module in (reference, dot, tlc, weather, collisions):
        print(f"\n=== Running {module.__name__} ===", flush=True)
        module.main()
    print("\nAll source extraction completed. Next run: python -m scripts.load_sources")

if __name__ == "__main__":
    main()
