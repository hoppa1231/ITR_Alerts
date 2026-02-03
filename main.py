import argparse
import sys

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None

from itr_alerts.config import Config
from itr_alerts.runner import run_once, run_schedule, setup_logging


def main() -> int:
    if load_dotenv:
        load_dotenv()

    setup_logging()

    parser = argparse.ArgumentParser(description="Snipe-IT license expiry notifier")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--schedule", action="store_true", help="Run in scheduler mode")
    args = parser.parse_args()

    config = Config()
    config.normalize()
    config.validate()

    if args.schedule:
        config.run_mode = "schedule"
    if args.once:
        config.run_mode = "once"

    if config.run_mode == "schedule":
        return run_schedule(config)
    return run_once(config)


if __name__ == "__main__":
    sys.exit(main())
