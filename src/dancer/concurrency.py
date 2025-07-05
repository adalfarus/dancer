"""TBA"""
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor, Future as _Future
# We basically need to change the way the threads work and thus need these
from concurrent.futures.thread import _threads_queues, _shutdown, _base
from threading import Event as _Event, Lock as _TLock, Thread as _Thread, current_thread as _current_thread
from multiprocessing.shared_memory import SharedMemory as _SharedMemory
from multiprocessing.synchronize import RLock as _RMLockT
from multiprocessing import RLock as _RMLock
import weakref
import struct
import queue
