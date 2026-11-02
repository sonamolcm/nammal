import logging
from django.utils import timezone
from .models import User, Notification

logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import messaging
except ImportError:
    firebase_admin = None
    messaging = None


def get_fcm_stats():
    """Returns summary statistics about registered devices / FCM tokens."""
    total_users_count = User.objects.filter(is_superuser=False).count()
    users_with_token = User.objects.filter(
        is_superuser=False
    ).exclude(fcm_token__isnull=True).exclude(fcm_token='').count()

    regular_users_with_token = User.objects.filter(
        is_superuser=False, is_staff=False
    ).exclude(fcm_token__isnull=True).exclude(fcm_token='').count()

    agents_with_token = User.objects.filter(
        is_superuser=False, is_staff=True
    ).exclude(fcm_token__isnull=True).exclude(fcm_token='').count()

    total_notifications = Notification.objects.count()

    return {
        'total_users_count': total_users_count,
        'users_with_token': users_with_token,
        'regular_users_with_token': regular_users_with_token,
        'agents_with_token': agents_with_token,
        'total_notifications': total_notifications,
    }


def send_fcm_notification(title, body, target_audience='all', recipient=None, image_url=None, extra_data=None):
    """
    Sends Firebase push notification to targeted users/agents and logs it in the database.

    :param title: Notification title
    :param body: Notification body text
    :param target_audience: 'all', 'users', 'agents', or 'specific'
    :param recipient: User instance (required if target_audience is 'specific')
    :param image_url: Optional image URL to display in push notification
    :param extra_data: Optional dict of key-value pairs passed in notification data payload
    :return: dict with {success, sent_count, failed_count, total_targets, notification, message}
    """
    title = (title or '').strip()
    body = (body or '').strip()

    if not title or not body:
        return {
            'success': False,
            'sent_count': 0,
            'failed_count': 0,
            'total_targets': 0,
            'notification': None,
            'message': 'Title and message body are required.'
        }

    # 1. Identify target users
    if target_audience == 'specific':
        if not recipient:
            return {
                'success': False,
                'sent_count': 0,
                'failed_count': 0,
                'total_targets': 0,
                'notification': None,
                'message': 'Recipient user must be specified for specific notifications.'
            }
        target_users = User.objects.filter(id=recipient.id)
    elif target_audience == 'users':
        target_users = User.objects.filter(is_superuser=False, is_staff=False)
    elif target_audience == 'agents':
        target_users = User.objects.filter(is_superuser=False, is_staff=True)
    else:  # 'all'
        target_audience = 'all'
        target_users = User.objects.filter(is_superuser=False)

    # 2. Extract valid non-empty tokens
    token_user_map = {}
    for u in target_users.exclude(fcm_token__isnull=True).exclude(fcm_token=''):
        tok = (u.fcm_token or '').strip()
        if tok:
            token_user_map[tok] = u

    tokens = list(token_user_map.keys())

    # 3. Create Notification record in Database
    notification_obj = Notification.objects.create(
        title=title,
        body=body,
        image_url=image_url if image_url else None,
        target_audience=target_audience,
        recipient=recipient if target_audience == 'specific' else None,
        sent_count=0,
        failed_count=0,
        created_at=timezone.now()
    )

    if not tokens:
        return {
            'success': True,
            'sent_count': 0,
            'failed_count': 0,
            'total_targets': 0,
            'notification': notification_obj,
            'message': 'Notification saved in app history, but no active device FCM tokens were found for this audience.'
        }

    # 4. Check Firebase Admin SDK
    if not messaging or not firebase_admin or not getattr(firebase_admin, '_apps', None):
        return {
            'success': True,
            'sent_count': 0,
            'failed_count': len(tokens),
            'total_targets': len(tokens),
            'notification': notification_obj,
            'message': 'Notification recorded in DB, but Firebase Admin SDK is not initialized.'
        }

    # 5. Build Notification & Data payloads
    notification_payload = messaging.Notification(
        title=title,
        body=body,
        image=image_url if image_url else None
    )

    data_payload = {
        'title': str(title),
        'body': str(body),
        'click_action': 'FLUTTER_NOTIFICATION_CLICK',
        'notification_id': str(notification_obj.id),
        'target_audience': str(target_audience),
        'type': str((extra_data or {}).get('type', 'general')),
    }
    if image_url:
        data_payload['image'] = str(image_url)
    if extra_data:
        for k, v in extra_data.items():
            data_payload[str(k)] = str(v)

    # 6. Send in batches (up to 500 per batch)
    success_count = 0
    failure_count = 0
    invalid_tokens = []

    batch_size = 500
    for i in range(0, len(tokens), batch_size):
        batch = tokens[i:i + batch_size]
        message_list = [
            messaging.Message(
                notification=notification_payload,
                data=data_payload,
                token=tok
            )
            for tok in batch
        ]

        try:
            batch_response = messaging.send_each(message_list)
            success_count += batch_response.success_count
            failure_count += batch_response.failure_count

            # Check individual responses for expired/invalid tokens
            for idx, resp in enumerate(batch_response.responses):
                if not resp.success and resp.exception:
                    exc = resp.exception
                    # Unregistered tokens (app uninstalled / token rotated)
                    if hasattr(exc, 'code') and exc.code in ['registration-token-not-registered', 'invalid-argument']:
                        invalid_tokens.append(batch[idx])
        except Exception as e:
            logger.error(f"Error sending batch push notifications: {e}")
            failure_count += len(batch)

    # Clean up stale/unregistered tokens if any
    if invalid_tokens:
        User.objects.filter(fcm_token__in=invalid_tokens).update(fcm_token=None)

    # 7. Update notification record
    notification_obj.sent_count = success_count
    notification_obj.failed_count = failure_count
    notification_obj.save()

    return {
        'success': True,
        'sent_count': success_count,
        'failed_count': failure_count,
        'total_targets': len(tokens),
        'notification': notification_obj,
        'message': f"Sent to {success_count} device(s) successfully ({failure_count} failed)."
    }
