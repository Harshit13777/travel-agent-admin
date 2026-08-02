class BaseQueueTransport:
    def enqueue(self, notification_id):
        raise NotImplementedError

class DatabaseQueueTransport(BaseQueueTransport):
    def enqueue(self, notification_id):
        # Already in DB with PENDING status. Cron will pick it up.
        pass

class RedisQueueTransport(BaseQueueTransport):
    def enqueue(self, notification_id):
        # celery_send.delay(notification_id)
        pass
