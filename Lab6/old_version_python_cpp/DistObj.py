# Save this as distributed_example.py

from multiprocessing.managers import BaseManager
from multiprocessing import Lock, Value, Process, Manager
import threading
import time
import queue
import uuid

class SharedState:
    def __init__(self, initial_value=None):
        self.value = initial_value
        self.lock = threading.Lock()
    
    def get_value(self):
        with self.lock:
            return self.value
            
    def set_value(self, new_value):
        with self.lock:
            self.value = new_value

class TokenManager:
    def __init__(self, total_processes=1):
        self._total_processes = Value('i', total_processes)
        self._available_tokens = Value('i', total_processes)
        self._lock = Lock()
        self._token_queue = queue.Queue()
        for _ in range(total_processes):
            self._token_queue.put(1)
        self._shared_state = SharedState()
    
    def get_total_processes(self):
        with self._total_processes.get_lock():
            return self._total_processes.value
    
    def get_shared_value(self):
        return self._shared_state.get_value()
    
    def set_shared_value(self, value):
        self._shared_state.set_value(value)
            
    def acquire_tokens(self, count):
        acquired = 0
        while acquired < count:
            token = self._token_queue.get()
            acquired += 1
        with self._available_tokens.get_lock():
            self._available_tokens.value -= count
    
    def release_tokens(self, count):
        for _ in range(count):
            self._token_queue.put(1)
        with self._available_tokens.get_lock():
            self._available_tokens.value += count
    
    def add_process(self):
        with self._total_processes.get_lock():
            self._total_processes.value += 1
            self._token_queue.put(1)

class DistObj:
    def __init__(self, val=None):
        self._initial_value = val
        self._id = str(uuid.uuid4())
        self._token_manager = None
        self._manager = None
        self._lock = Lock()
        
    def initialize_networking(self, host='localhost', port=50000):
        BaseManager.register('TokenManager', TokenManager, 
                           exposed=['acquire_tokens', 'release_tokens', 
                                  'add_process', 'get_total_processes',
                                  'get_shared_value', 'set_shared_value'])
        
        self._manager = BaseManager(address=(host, port), authkey=b'secret')
        
        try:
            self._manager.connect()
            self._token_manager = self._manager.TokenManager()
            self._token_manager.add_process()
        except:
            self._manager.start()
            self._token_manager = self._manager.TokenManager()
            if self._initial_value is not None:
                self._token_manager.set_shared_value(self._initial_value)
            
    def read(self):
        with self._lock:
            self._token_manager.acquire_tokens(1)
            try:
                result = self._token_manager.get_shared_value()
                return result
            finally:
                self._token_manager.release_tokens(1)
    
    def write(self, value):
        with self._lock:
            total_tokens = self._token_manager.get_total_processes()
            self._token_manager.acquire_tokens(total_tokens)
            try:
                self._token_manager.set_shared_value(value)
            finally:
                self._token_manager.release_tokens(total_tokens)

def worker(process_id, port):
    print(f"Process {process_id} starting...")
    try:
        dist_obj = DistObj(f"Initial value from process {process_id}" if process_id == 0 else None)
        dist_obj.initialize_networking(port=port)
        
        # Perform some operations
        time.sleep(1)  # Give other processes time to start
        
        current_value = dist_obj.read()
        print(f"Process {process_id} read: {current_value}")
        
        new_value = f"New value from process {process_id}"
        print(f"Process {process_id} writing: {new_value}")
        dist_obj.write(new_value)
        
        time.sleep(1)  # Give time for other processes to read
        
        final_value = dist_obj.read()
        print(f"Process {process_id} final read: {final_value}")
        
    except Exception as e:
        import traceback
        print(f"Process {process_id} encountered error: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    processes = []
    base_port = 50000
    num_processes = 3
    
    print("Starting distributed object demonstration...")
    
    try:
        # Start processes
        for i in range(num_processes):
            p = Process(target=worker, args=(i, base_port))
            processes.append(p)
            p.start()
            time.sleep(0.5)  # Delay between process starts
        
        # Wait for all processes to complete
        for p in processes:
            p.join()
            
    except KeyboardInterrupt:
        print("\nStopping all processes...")
        for p in processes:
            p.terminate()
            
    finally:
        print("Demonstration completed.")