from queue import Queue


class PeekableQueue(Queue):
    def peek(self):
        if not self.empty():
            return list(self.queue)
        return []
