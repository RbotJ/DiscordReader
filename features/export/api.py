"""Export API Blueprint

Provides endpoints for downloading ingested Discord messages as JSON
filtered by channel, author, and date range.
"""
import io
import json
import logging
from datetime import datetime
from flask import Blueprint, request, send_file, jsonify

from .service import get_messages

logger = logging.getLogger(__name__)

export_bp = Blueprint('export_api', __name__, url_prefix='/api/export')


def parse_date(value: str) -> datetime | None:
    """Parse ISO date string to datetime."""
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


@export_bp.route('/messages', methods=['GET'])
def export_messages():
    """Download messages filtered by query parameters as a JSON file."""
    channel = request.args.get('channel')
    author = request.args.get('author')
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    limit = int(request.args.get('limit', '1000'))

    start = parse_date(start_str) if start_str else None
    end = parse_date(end_str) if end_str else None

    messages = get_messages(channel, author, start, end, limit)

    buffer = io.BytesIO()
    buffer.write(json.dumps(messages, indent=2).encode('utf-8'))
    buffer.seek(0)

    filename = f"messages_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/json'
    )


@export_bp.route('/messages.json', methods=['GET'])
def export_messages_json():
    """Return messages as JSON without download headers."""
    channel = request.args.get('channel')
    author = request.args.get('author')
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    limit = int(request.args.get('limit', '1000'))

    start = parse_date(start_str) if start_str else None
    end = parse_date(end_str) if end_str else None

    messages = get_messages(channel, author, start, end, limit)
    return jsonify({'count': len(messages), 'messages': messages})
