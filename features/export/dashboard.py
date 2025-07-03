"""Export Dashboard Blueprint

Provides a simple interface to download messages using the export API.
"""
from flask import Blueprint, render_template

export_dashboard_bp = Blueprint(
    'export_dashboard', __name__,
    template_folder='templates',
    url_prefix='/dashboard/export'
)


@export_dashboard_bp.route('/')
def overview():
    """Render the export interface."""
    return render_template('export/overview.html')
