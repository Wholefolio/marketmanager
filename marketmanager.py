#!/usr/bin/env python3
"""MarketManager daemon."""
from django.conf import settings
from multiprocessing import Process
from time import sleep
import logging

from marketmanager.marketmanager import MarketManager
from daemonlib.tools import main
from daemonlib.app import App


class MarketManagerApp(App):
    """MarketManagerApp main entry point."""

    def run(self, *args):
        """Override the run method."""
        # The stats must be shared across both processes, hence the shared
        # dict from Manager
        logger = logging.getLogger("MarketManagerApp")
        manager = MarketManager(**self.config)
        # Start the processes
        logger.info("Starting incoming process.")
        incoming = Process(target=manager.incoming, name="IncomingProcess")
        incoming.start()
        with open(self.pidfile, "a+") as f:
            f.write("{}\n".format(incoming.pid))
        logger.info("Starting polling process.")
        poller = Process(target=manager.poller, name="PollerProcess")
        poller.start()
        with open(self.pidfile, "a+") as f:
            f.write("{}\n".format(poller.pid))
        logger.info("Starting scheduling process.")
        scheduler = Process(target=manager.scheduler, name="SchedulerProcess")
        scheduler.start()
        with open(self.pidfile, "a+") as f:
            f.write("{}\n".format(scheduler.pid))
        proc_dict = {"incoming": incoming, "poller": poller,
                     "scheduler": scheduler}
        while True:
            for name, proc in proc_dict.items():
                if not proc.is_alive:
                    msg = "Process {} has died. Trying to restart".format(name)
                    logger.critical(msg)
                    process_function = getattr(MarketManager, name)
                    temp_proc = Process(target=process_function, name=name)
                    temp_proc.start()
                sleep(5)


if __name__ == "__main__":
    main("marketmanager", MarketManagerApp, settings.MARKET_MANAGER_DAEMON)
