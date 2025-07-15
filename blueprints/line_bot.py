# ============================================================================
# blueprints/line_bot.py - Simple LINE Bot Blueprint
# ============================================================================

from flask import Blueprint

line_bp = Blueprint('line_bot', __name__)

@line_bp.route('/webhook', methods=['POST'])
def webhook():
    """LINE Bot webhook"""
    return 'OK'