import asyncio
import threading
from functools import wraps
from typing import TypeVar, ParamSpec, Callable, Any, Coroutine

P = ParamSpec("P")
T = TypeVar("T")


def async_to_sync(async_func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, T]:
    """
    Convert an async function to a synchronous function.

    This wrapper runs the async function in a separate thread with its own
    event loop, allowing it to be called from synchronous code even when
    an event loop is already running.

    Args:
        async_func: The async function to wrap

    Returns:
        A synchronous version of the function
    """

    @wraps(async_func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        result = []
        exception = []

        def run_in_new_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result.append(loop.run_until_complete(async_func(*args, **kwargs)))
            except Exception as e:
                exception.append(e)
            finally:
                loop.close()

        thread = threading.Thread(target=run_in_new_loop)
        thread.start()
        thread.join()

        if exception:
            raise exception[0]

        return result[0]

    return wrapper
