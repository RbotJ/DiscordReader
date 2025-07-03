"""Simple CLI for exporting messages."""
import argparse
import json
from datetime import datetime

from .service import get_messages


def parse_date(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Export Discord messages to JSON")
    parser.add_argument('--channel', help='Channel ID')
    parser.add_argument('--author', help='Author ID')
    parser.add_argument('--start', help='Start datetime (ISO format)')
    parser.add_argument('--end', help='End datetime (ISO format)')
    parser.add_argument('--limit', type=int, default=1000, help='Max messages')
    parser.add_argument('outfile', help='Output file path')
    args = parser.parse_args()

    start = parse_date(args.start) if args.start else None
    end = parse_date(args.end) if args.end else None

    messages = get_messages(args.channel, args.author, start, end, args.limit)

    with open(args.outfile, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2)

    print(f"Exported {len(messages)} messages to {args.outfile}")


if __name__ == '__main__':
    main()
