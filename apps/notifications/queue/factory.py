from django.conf import settings
from .transport import DatabaseQueueTransport, RedisQueueTransport
from .worker import CronWorker, CeleryWorker

class QueueFactory:
    @classmethod
    def get(cls):
        backend = getattr(settings, 'NOTIFICATION_QUEUE_BACKEND', 'DATABASE')
        if backend == 'REDIS':
            return RedisQueueTransport()
        return DatabaseQueueTransport()


class WorkerFactory:
    @classmethod
    def get(cls):
        backend = getattr(settings, 'NOTIFICATION_WORKER', 'CRON')
        if backend == 'CELERY':
            return CeleryWorker()
        return CronWorker()
