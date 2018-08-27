#!/usr/bin/env python3
"""MarketManager daemon."""

from multiprocessing import Process
from marketmanager.marketmanager import MarketManager
from daemonlib.tools import main
from daemonlib.app import App
from django.conf import settings 


class MarketManagerApp(App):
    """MarketManagerApp main entry point."""

    def run(self, *args):
        """Override the run method."""
        # The stats must be shared across both processes, hence the shared
        # dict from Manager
        manager = MarketManager(**self.config)
        # Start the incoming request listener in a separate Process
        inc = Process(target=manager.incoming, name="IncomingProcess")
        inc.start()
        with open(self.pidfile, "a+") as f:
            f.write("{}\n".format(inc.pid))
        poller = Process(target=manager.poller, name="PollerProcess")
        poller.start()
        with open(self.pidfile, "a+") as f:
            f.write("{}\n".format(poller.pid))
        manager.main()


if __name__ == "__main__":
    main("marketmanager", MarketManagerApp, settings.MARKET_MANAGER_DAEMON)
