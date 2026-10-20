"""Request identity is server-owned; it is never read from a JSON payload."""
from contextvars import ContextVar

current_actor = ContextVar("localauthor_actor", default=None)
current_author = ContextVar("localauthor_author", default=None)
current_request = ContextVar("localauthor_request", default=None)


def response_metadata(metadata):
    return {**metadata, **({'request_id':current_request.get()} if current_request.get() else {})}


def message_metadata(input_format):
    metadata = {"format": input_format}
    if current_actor.get():
        metadata.update(author_id=current_actor.get(), author_name=current_author.get())
    return response_metadata(metadata)
