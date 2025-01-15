from flask import Blueprint, request, jsonify

from ..services.notification_service import NotificationService
from ..utils.security import jwt_required, get_current_user_id

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/', methods=['GET'])
@jwt_required
def get_notifications():
    try:
        user_id = get_current_user_id()
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        notifications = NotificationService.get_notifications(user_id, unread_only)

        return jsonify([{
            'notification_id': str(notif.notification_id),
            'message': notif.message,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat()
        } for notif in notifications]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@notifications_bp.route('/<notification_id>/read', methods=['PUT'])
@jwt_required
def mark_as_read(notification_id):
    try:
        user_id = get_current_user_id()
        NotificationService.mark_as_read(user_id, notification_id)
        return jsonify({'message': 'Notification marked as read'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
