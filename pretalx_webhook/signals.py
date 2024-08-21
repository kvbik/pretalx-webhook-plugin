import json
import requests
import logging
from django.dispatch import receiver
from django.urls import reverse
from django.conf import settings
from pretalx.orga.signals import nav_event_settings
from pretalx.schedule.signals import schedule_release

logger = logging.getLogger(__name__)

class CustomJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            return {key: self.default(value) for key, value in vars(obj).items() 
                    if not key.startswith('_') and not callable(value)}
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

def log_object_attributes(obj, logger):
    try:
        attributes = json.dumps(obj, cls=CustomJSONEncoder, indent=2)
        logger.error(f"Object attributes for {type(obj).__name__}:\n{attributes}")
    except Exception as e:
        logger.error(f"Error logging attributes for {type(obj).__name__}: {str(e)}")


@receiver(schedule_release, dispatch_uid="pretalx_webhook_schedule_release")
def on_schedule_release(sender, schedule, user, **kwargs):
    try:
        # Get the webhook settings for this event
        webhook_settings = settings.PLUGIN_SETTINGS["pretalx_webhook"]
        if not webhook_settings:
            logger.info(f"Webhook settings are empty or invalid for event {sender.slug}")
            return

        webhook_endpoint = webhook_settings["endpoint"]
        webhook_secret = webhook_settings["secret"]

        if not webhook_endpoint:
            logger.info(f"Webhook endpoint is empty for event {sender.slug}")
            return
        
        # log the arguments 
        logger.info(f"Log all arguments..")
        log_object_attributes(sender, logger)
        log_object_attributes(schedule, logger)
        log_object_attributes(user, logger)
        log_object_attributes(kwargs, logger)

        payload = {
            'sender': str(sender),
            'schedule': str(schedule),
            'user': str(user),
        }

        logger.error(f"Prepare payload..")
        logger.error(payload)

        headers = {'Content-Type': 'application/json'}
        if webhook_secret:
            headers['X-Webhook-Secret'] = webhook_secret
        else:
            logger.warning(f"Webhook secret is empty for event {sender.slug}")


        logger.error(f"Send JSON request..")
        response = requests.post(webhook_endpoint,
            json=json.dumps(payload),
            headers=headers,
        )
        
        if response.status_code == 200:
            logger.info(f"Webhook sent successfully for event {sender.slug}")
        else:
            logger.error(f"Webhook failed for event {sender.slug}. Status code: {response.status_code}")

    except Exception as e:
        logger.error(f"Error sending webhook for event {sender.slug}: {str(e)}")