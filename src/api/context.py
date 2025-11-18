"""Context variable for the API."""

from contextvars import ContextVar
from mcp.server.fastmcp import Context
from functools import wraps
import inspect
from typing import Callable, Dict, Any

# Context variable to hold the current context object of a given tool call
session_context = ContextVar("session_context")


def get_session_context() -> Context | None:
    return session_context.get(None)


# Using session's context to store session-specific settings like org_id
def get_session_settings() -> Dict[str, Any] | None:
    current_context = get_session_context()
    if current_context is not None:
        return current_context.request_context.lifespan_context

    raise Exception(
        "No session context available for this tool call, please try again."
    )


def tool_wrapper(func: Callable) -> Callable:
    """
    This function wraps tool functions to set the context variable.
    """

    # Check if the underlying function accepts a 'ctx' parameter, or generic **kwargs
    func_signature = inspect.signature(func)
    accepts_ctx = "ctx" in func_signature.parameters or any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in func_signature.parameters.values()
    )

    @wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        # Ensures that ctx is passed to the original function if it accepts it
        kwargs_cpy = dict(kwargs)
        if accepts_ctx:
            kwargs_cpy["ctx"] = ctx

        current_context = get_session_context()
        if ctx is not None and current_context is None:
            session_context.set(ctx.request_context)

        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs_cpy)
        else:
            return func(*args, **kwargs_cpy)

    # Ensures the mcp library knows that the wrapper expects a 'ctx' parameter
    if not accepts_ctx:
        wrapper.__annotations__["ctx"] = Context

    return wrapper
