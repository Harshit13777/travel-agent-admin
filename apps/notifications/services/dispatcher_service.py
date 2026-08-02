class DispatcherService:
    """
    Worker uses this service.
    Responsibilities:
    Pick Pending -> Lock -> Render -> Choose Provider -> Send -> Update Status -> Log
    """

    @classmethod
    def process_pending(cls):
        pass
