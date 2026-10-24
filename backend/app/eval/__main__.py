import asyncio
import sys

from .runner import print_report, run_eval


def main() -> None:
    datasource_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    report = asyncio.run(run_eval(datasource_id))
    print_report(report)


if __name__ == "__main__":
    main()

