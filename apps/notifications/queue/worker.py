class BaseWorker:
    def process(self, notification_id):
        pass

class CronWorker(BaseWorker):
    def process(self, notification_id):
        # Calls Dispatcher
        pass

class CeleryWorker(BaseWorker):
    def process(self, notification_id):
        # Calls Dispatcher
        pass
