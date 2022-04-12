import threading
import asyncore
import select

class AsyncoreThread(threading.Thread):
    """ Asyncore thread class """
    def __init__(self, timeout=30.0, use_poll=0,map=None):
        self.flag=True
        self.timeout=5
        self.use_poll=use_poll
        self.map=map
        threading.Thread.__init__(self, None, None, 'asyncore thread')

    def run(self):

        self.loop()

    def loop(self):
    # print 'In AsyncoreThread:loop...'
        if self.map is None:
            self.map = asyncore.socket_map

        if self.use_poll:
            if hasattr(select, 'poll'):
                poll_fun = asyncore.poll3
            else:
                poll_fun = asyncore.poll2
        else:
            # print 'Using asyncore.poll...'
            poll_fun=asyncore.poll

            while self.map and self.flag:
                poll_fun(self.timeout,self.map)


        def end(self):
            print('Ending asyncore loop...')
            self.flag=False
            self.map=None