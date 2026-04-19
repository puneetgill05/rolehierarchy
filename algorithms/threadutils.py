import concurrent.futures

from abc import ABC, abstractmethod
from threading import current_thread
import threading

class MyTask(ABC):
    def __init__(self, num_workers=3):
        self.num_workers = num_workers
        self.futures = []

    @abstractmethod
    def task(self, param):
        pass

    @abstractmethod
    def pre_execute(self, args):
        pass

    @abstractmethod
    def post_execute(self, result):
        pass

    # function for initializing the worker thread
    def initializer_worker(self):
        # get the unique name for this thread
        name = current_thread().name
        # store the unique worker name in a thread local variable
        print(f'Initializing worker thread {name}')

    def execute(self, params):
        # Using ThreadPoolExecutor
        with (concurrent.futures.ThreadPoolExecutor(thread_name_prefix='MyTaskExecutor',
                                                    max_workers=self.num_workers, initializer=self.initializer_worker) as
              executor):
            # Submit multiple tasks
            for param in params:
                self.futures.append(executor.submit(self.task, param))

            # Retrieve results as they complete

            # for future in concurrent.futures.as_completed(self.futures):
            #     result = future.result()
            #     print(f"Result: {result}")
            #     self.post_execute(result)
            concurrent.futures.wait(self.futures)
            self.post_execute(None)