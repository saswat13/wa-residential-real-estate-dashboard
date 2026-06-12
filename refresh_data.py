import argparse

from data_sources import refresh_redfin_cache


def main():
    parser = argparse.ArgumentParser(description="Refresh cached Washington Redfin data.")
    parser.add_argument(
        "level",
        choices=["state", "county", "city", "zip"],
        default="county",
        nargs="?",
    )
    args = parser.parse_args()

    refreshed = refresh_redfin_cache(args.level)
    print(f"Refreshed {args.level} data: {len(refreshed):,} rows")


if __name__ == "__main__":
    main()
