"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import array
import asyncio
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Collection,
    Coroutine,
    Dict,
    ForwardRef,
    Generic,
    Iterable,
    Iterator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Protocol,
    Set,
    Sequence,
    SupportsIndex,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
    TYPE_CHECKING,
)
import collections
import unicodedata
from base64 import b64encode, b64decode
from bisect import bisect_left
import datetime
import functools
from inspect import isawaitable as _isawaitable, signature as _signature
from operator import attrgetter
from urllib.parse import urlencode
import json
import logging
import os
import random
import re
import string
import sys
from threading import Timer
import types
import typing
import warnings
import logging
import zlib
import struct
import time
import yarl
import uuid

try:
    import orjson  # type: ignore
except ModuleNotFoundError:
    HAS_ORJSON = False
else:
    HAS_ORJSON = True


try:
    import zstandard  # type: ignore
except ImportError:
    HAS_ZSTD = False
else:
    HAS_ZSTD = True

from .enums import Locale, try_enum

__all__ = (
    'oauth_url',
    'snowflake_time',
    'snowflake_worker_id',
    'snowflake_process_id',
    'snowflake_increment',
    'time_snowflake',
    'find',
    'get',
    'sleep_until',
    'utcnow',
    'remove_markdown',
    'escape_markdown',
    'escape_mentions',
    'maybe_coroutine',
    'as_chunks',
    'format_dt',
    'set_target',
    'MISSING',
    'setup_logging',
)

DISCORD_EPOCH = 1420070400000
DEFAULT_FILE_SIZE_LIMIT_BYTES = 10485760

_log = logging.getLogger(__name__)


class _MissingSentinel:
    __slots__ = ()

    def __eq__(self, other):
        return False

    def __bool__(self):
        return False

    def __hash__(self):
        return 0

    def __repr__(self):
        return '...'


MISSING: Any = _MissingSentinel()


class _cached_property:
    def __init__(self, function):
        self.function = function
        self.__doc__ = getattr(function, '__doc__')

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = self.function(instance)
        setattr(instance, self.function.__name__, value)

        return value


if TYPE_CHECKING:
    from aiohttp import BasicAuth, ClientSession
    from functools import cached_property as cached_property

    from typing_extensions import ParamSpec, Self, TypeGuard

    from .permissions import Permissions
    from .abc import Messageable, Snowflake
    from .invite import Invite
    from .message import Message
    from .template import Template
    from .commands import ApplicationCommand
    from .entitlements import Gift

    class _DecompressionContext(Protocol):
        COMPRESSION_TYPE: str

        def decompress(self, data: bytes, /) -> str | None:
            ...

    P = ParamSpec('P')

    MaybeAwaitableFunc = Callable[P, 'MaybeAwaitable[T]']

    _SnowflakeListBase = array.array[int]

else:
    cached_property = _cached_property
    _SnowflakeListBase = array.array


T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
_Iter = Union[Iterable[T], AsyncIterable[T]]
Coro = Coroutine[Any, Any, T]
MaybeAwaitable = Union[T, Awaitable[T]]


class CachedSlotProperty(Generic[T, T_co]):
    def __init__(self, name: str, function: Callable[[T], T_co]) -> None:
        self.name = name
        self.function = function
        self.__doc__ = getattr(function, '__doc__')

    @overload
    def __get__(self, instance: None, owner: Type[T]) -> CachedSlotProperty[T, T_co]:
        ...

    @overload
    def __get__(self, instance: T, owner: Type[T]) -> T_co:
        ...

    def __get__(self, instance: Optional[T], owner: Type[T]) -> Any:
        if instance is None:
            return self

        try:
            return getattr(instance, self.name)
        except AttributeError:
            value = self.function(instance)
            setattr(instance, self.name, value)
            return value


class classproperty(Generic[T_co]):
    def __init__(self, fget: Callable[[Any], T_co]) -> None:
        self.fget = fget

    def __get__(self, instance: Optional[Any], owner: Type[Any]) -> T_co:
        return self.fget(owner)

    def __set__(self, instance: Optional[Any], value: Any) -> None:
        raise AttributeError('cannot set attribute')


def cached_slot_property(name: str) -> Callable[[Callable[[T], T_co]], CachedSlotProperty[T, T_co]]:
    def decorator(func: Callable[[T], T_co]) -> CachedSlotProperty[T, T_co]:
        return CachedSlotProperty(name, func)

    return decorator


class SequenceProxy(Sequence[T_co]):
    """A proxy of a sequence that only creates a copy when necessary."""

    def __init__(self, proxied: Collection[T_co], *, sorted: bool = False):
        self.__proxied: Collection[T_co] = proxied
        self.__sorted: bool = sorted

    @cached_property
    def __copied(self) -> List[T_co]:
        if self.__sorted:
            # The type checker thinks the variance is wrong, probably due to the comparison requirements
            self.__proxied = sorted(self.__proxied)  # type: ignore
        else:
            self.__proxied = list(self.__proxied)
        return self.__proxied

    def __repr__(self) -> str:
        return f"SequenceProxy({self.__proxied!r})"

    @overload
    def __getitem__(self, idx: SupportsIndex) -> T_co:
        ...

    @overload
    def __getitem__(self, idx: slice) -> List[T_co]:
        ...

    def __getitem__(self, idx: Union[SupportsIndex, slice]) -> Union[T_co, List[T_co]]:
        return self.__copied[idx]

    def __len__(self) -> int:
        return len(self.__proxied)

    def __contains__(self, item: Any) -> bool:
        return item in self.__copied

    def __iter__(self) -> Iterator[T_co]:
        return iter(self.__copied)

    def __reversed__(self) -> Iterator[T_co]:
        return reversed(self.__copied)

    def index(self, value: Any, *args: Any, **kwargs: Any) -> int:
        return self.__copied.index(value, *args, **kwargs)

    def count(self, value: Any) -> int:
        return self.__copied.count(value)


@overload
def parse_time(timestamp: None) -> None:
    ...


@overload
def parse_time(timestamp: str) -> datetime.datetime:
    ...


@overload
def parse_time(timestamp: Optional[str]) -> Optional[datetime.datetime]:
    ...


def parse_time(timestamp: Optional[str]) -> Optional[datetime.datetime]:
    if timestamp:
        return datetime.datetime.fromisoformat(timestamp)
    return None


@overload
def parse_date(date: None) -> None:
    ...


@overload
def parse_date(date: str) -> datetime.date:
    ...


@overload
def parse_date(date: Optional[str]) -> Optional[datetime.date]:
    ...


def parse_date(date: Optional[str]) -> Optional[datetime.date]:
    if date:
        return parse_time(date).date()
    return None


@overload
def parse_timestamp(timestamp: None, *, ms: bool = True) -> None:
    ...


@overload
def parse_timestamp(timestamp: float, *, ms: bool = True) -> datetime.datetime:
    ...


@overload
def parse_timestamp(timestamp: Optional[float], *, ms: bool = True) -> Optional[datetime.datetime]:
    ...


def parse_timestamp(timestamp: Optional[float], *, ms: bool = True) -> Optional[datetime.datetime]:
    if timestamp:
        if ms:
            timestamp /= 1000
        return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


def copy_doc(original: Callable[..., Any]) -> Callable[[T], T]:
    def decorator(overridden: T) -> T:
        overridden.__doc__ = original.__doc__
        overridden.__signature__ = _signature(original)  # type: ignore
        return overridden

    return decorator


def deprecated(instead: Optional[str] = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def actual_decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def decorated(*args: P.args, **kwargs: P.kwargs) -> T:
            warnings.simplefilter('always', DeprecationWarning)  # turn off filter
            if instead:
                fmt = "{0.__name__} is deprecated, use {1} instead."
            else:
                fmt = '{0.__name__} is deprecated.'

            warnings.warn(fmt.format(func, instead), stacklevel=3, category=DeprecationWarning)
            warnings.simplefilter('default', DeprecationWarning)  # reset filter
            return func(*args, **kwargs)

        return decorated

    return actual_decorator


def oauth_url(
    client_id: Union[int, str],
    *,
    permissions: Permissions = MISSING,
    guild: Snowflake = MISSING,
    redirect_uri: str = MISSING,
    scopes: Iterable[str] = MISSING,
    disable_guild_select: bool = False,
    state: str = MISSING,
) -> str:
    """A helper function that returns the OAuth2 URL for inviting a bot
    into guilds.

    .. versionchanged:: 2.0

        ``permissions``, ``guild``, ``redirect_uri``, ``scopes`` and ``state`` parameters
        are now keyword-only.

    Parameters
    -----------
    client_id: Union[:class:`int`, :class:`str`]
        The client ID for the bot.
    permissions: :class:`~discord.Permissions`
        The permissions you're requesting. If not given then you won't be requesting any
        permissions.
    guild: :class:`~discord.abc.Snowflake`
        The guild to pre-select in the authorization screen, if available.
    redirect_uri: :class:`str`
        An optional valid redirect URI.
    scopes: Iterable[:class:`str`]
        An optional valid list of scopes. Defaults to ``('bot', 'applications.commands')``.

        .. versionadded:: 1.7
    disable_guild_select: :class:`bool`
        Whether to disallow the user from changing the guild dropdown.

        .. versionadded:: 2.0
    state: :class:`str`
        The state to return after the authorization.

        .. versionadded:: 2.0

    Returns
    --------
    :class:`str`
        The OAuth2 URL for inviting the bot into guilds.
    """
    url = f'https://discord.com/oauth2/authorize?client_id={client_id}'
    url += '&scope=' + '+'.join(scopes or ('bot', 'applications.commands'))
    if permissions is not MISSING:
        url += f'&permissions={permissions.value}'
    if guild is not MISSING:
        url += f'&guild_id={guild.id}'
    if disable_guild_select:
        url += '&disable_guild_select=true'
    if redirect_uri is not MISSING:
        url += '&response_type=code&' + urlencode({'redirect_uri': redirect_uri})
    if state is not MISSING:
        url += f'&{urlencode({"state": state})}'
    return url


def snowflake_worker_id(id: int, /) -> int:
    """Returns the worker ID of the given snowflake

    .. versionadded:: 2.1

    Parameters
    -----------
    id: :class:`int`
        The snowflake ID.

    Returns
    --------
    :class:`int`
        The worker ID used to generate the snowflake.
    """
    return (id >> 17) & 0x1F


def snowflake_process_id(id: int, /) -> int:
    """Returns the process ID of the given snowflake

    .. versionadded:: 2.1

    Parameters
    -----------
    id: :class:`int`
        The snowflake ID.

    Returns
    --------
    :class:`int`
        The process ID used to generate the snowflake.
    """
    return (id >> 12) & 0x1F


def snowflake_increment(id: int, /) -> int:
    """Returns the increment of the given snowflake.
    For every generated ID on that process, this number is incremented.

    .. versionadded:: 2.1

    Parameters
    -----------
    id: :class:`int`
        The snowflake ID.

    Returns
    --------
    :class:`int`
        The increment of current snowflake.
    """
    return id & 0xFFF


def snowflake_time(id: int, /) -> datetime.datetime:
    """Returns the creation time of the given snowflake.

    .. versionchanged:: 2.0
        The ``id`` parameter is now positional-only.

    Parameters
    -----------
    id: :class:`int`
        The snowflake ID.

    Returns
    --------
    :class:`datetime.datetime`
        An aware datetime in UTC representing the creation time of the snowflake.
    """
    timestamp = ((id >> 22) + DISCORD_EPOCH) / 1000
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


def time_snowflake(dt: datetime.datetime, /, *, high: bool = False) -> int:
    """Returns a numeric snowflake pretending to be created at the given date.

    When using as the lower end of a range, use ``time_snowflake(dt, high=False) - 1``
    to be inclusive, ``high=True`` to be exclusive.

    When using as the higher end of a range, use ``time_snowflake(dt, high=True) + 1``
    to be inclusive, ``high=False`` to be exclusive.

    .. versionchanged:: 2.0
        The ``high`` parameter is now keyword-only and the ``dt`` parameter is now
        positional-only.

    Parameters
    -----------
    dt: :class:`datetime.datetime`
        A datetime object to convert to a snowflake.
        If naive, the timezone is assumed to be local time.
    high: :class:`bool`
        Whether or not to set the lower 22 bit to high or low.

    Returns
    --------
    :class:`int`
        The snowflake representing the time given.
    """
    discord_millis = int(dt.timestamp() * 1000 - DISCORD_EPOCH)
    return (discord_millis << 22) + (2**22 - 1 if high else 0)


def _find(predicate: Callable[[T], Any], iterable: Iterable[T], /) -> Optional[T]:
    return next((element for element in iterable if predicate(element)), None)


async def _afind(predicate: Callable[[T], Any], iterable: AsyncIterable[T], /) -> Optional[T]:
    async for element in iterable:
        if predicate(element):
            return element

    return None


@overload
def find(predicate: Callable[[T], Any], iterable: AsyncIterable[T], /) -> Coro[Optional[T]]:
    ...


@overload
def find(predicate: Callable[[T], Any], iterable: Iterable[T], /) -> Optional[T]:
    ...


def find(predicate: Callable[[T], Any], iterable: _Iter[T], /) -> Union[Optional[T], Coro[Optional[T]]]:
    r"""A helper to return the first element found in the sequence
    that meets the predicate. For example: ::

        member = discord.utils.find(lambda m: m.name == 'Mighty', channel.guild.members)

    would find the first :class:`~discord.Member` whose name is 'Mighty' and return it.
    If an entry is not found, then ``None`` is returned.

    This is different from :func:`py:filter` due to the fact it stops the moment it finds
    a valid entry.

    .. versionchanged:: 2.0

        Both parameters are now positional-only.

    .. versionchanged:: 2.0

        The ``iterable`` parameter supports :term:`asynchronous iterable`\s.

    Parameters
    -----------
    predicate
        A function that returns a boolean-like result.
    iterable: Union[:class:`collections.abc.Iterable`, :class:`collections.abc.AsyncIterable`]
        The iterable to search through. Using a :class:`collections.abc.AsyncIterable`,
        makes this function return a :term:`coroutine`.
    """

    return (
        _afind(predicate, iterable)  # type: ignore
        if hasattr(iterable, '__aiter__')  # isinstance(iterable, collections.abc.AsyncIterable) is too slow
        else _find(predicate, iterable)  # type: ignore
    )


def _get(iterable: Iterable[T], /, **attrs: Any) -> Optional[T]:
    # global -> local
    _all = all
    attrget = attrgetter

    # Special case the single element call
    if len(attrs) == 1:
        k, v = attrs.popitem()
        pred = attrget(k.replace('__', '.'))
        return next((elem for elem in iterable if pred(elem) == v), None)

    converted = [(attrget(attr.replace('__', '.')), value) for attr, value in attrs.items()]
    for elem in iterable:
        if _all(pred(elem) == value for pred, value in converted):
            return elem
    return None


async def _aget(iterable: AsyncIterable[T], /, **attrs: Any) -> Optional[T]:
    # global -> local
    _all = all
    attrget = attrgetter

    # Special case the single element call
    if len(attrs) == 1:
        k, v = attrs.popitem()
        pred = attrget(k.replace('__', '.'))
        async for elem in iterable:
            if pred(elem) == v:
                return elem
        return None

    converted = [(attrget(attr.replace('__', '.')), value) for attr, value in attrs.items()]

    async for elem in iterable:
        if _all(pred(elem) == value for pred, value in converted):
            return elem
    return None


@overload
def get(iterable: AsyncIterable[T], /, **attrs: Any) -> Coro[Optional[T]]:
    ...


@overload
def get(iterable: Iterable[T], /, **attrs: Any) -> Optional[T]:
    ...


def get(iterable: _Iter[T], /, **attrs: Any) -> Union[Optional[T], Coro[Optional[T]]]:
    r"""A helper that returns the first element in the iterable that meets
    all the traits passed in ``attrs``. This is an alternative for
    :func:`~discord.utils.find`.

    When multiple attributes are specified, they are checked using
    logical AND, not logical OR. Meaning they have to meet every
    attribute passed in and not one of them.

    To have a nested attribute search (i.e. search by ``x.y``) then
    pass in ``x__y`` as the keyword argument.

    If nothing is found that matches the attributes passed, then
    ``None`` is returned.

    .. versionchanged:: 2.0

        The ``iterable`` parameter is now positional-only.

    .. versionchanged:: 2.0

        The ``iterable`` parameter supports :term:`asynchronous iterable`\s.

    Examples
    ---------

    Basic usage:

    .. code-block:: python3

        member = discord.utils.get(message.guild.members, name='Foo')

    Multiple attribute matching:

    .. code-block:: python3

        channel = discord.utils.get(guild.voice_channels, name='Foo', bitrate=64000)

    Nested attribute matching:

    .. code-block:: python3

        channel = discord.utils.get(client.get_all_channels(), guild__name='Cool', name='general')

    Async iterables:

    .. code-block:: python3

        msg = await discord.utils.get(channel.history(), author__name='Dave')

    Parameters
    -----------
    iterable: Union[:class:`collections.abc.Iterable`, :class:`collections.abc.AsyncIterable`]
        The iterable to search through. Using a :class:`collections.abc.AsyncIterable`,
        makes this function return a :term:`coroutine`.
    \*\*attrs
        Keyword arguments that denote attributes to search with.
    """

    return (
        _aget(iterable, **attrs)  # type: ignore
        if hasattr(iterable, '__aiter__')  # isinstance(iterable, collections.abc.AsyncIterable) is too slow
        else _get(iterable, **attrs)  # type: ignore
    )


def _unique(iterable: Iterable[T]) -> List[T]:
    return [x for x in dict.fromkeys(iterable)]


def _get_as_snowflake(data: Any, key: str) -> Optional[int]:
    try:
        value = data[key]
    except KeyError:
        return None
    else:
        return value and int(value)


def _ocast(value: Any, type: Any):
    if value is MISSING:
        return MISSING
    return type(value)


def _get_mime_type_for_image(data: bytes, with_video: bool = False, fallback: bool = False) -> str:
    if data.startswith(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'):
        return 'image/png'
    elif data[0:3] == b'\xff\xd8\xff' or data[6:10] in (b'JFIF', b'Exif'):
        return 'image/jpeg'
    elif data.startswith((b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61')):
        return 'image/gif'
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'image/webp'
    elif data.startswith(b'\x66\x74\x79\x70\x69\x73\x6F\x6D') and with_video:
        return 'video/mp4'
    else:
        if fallback:
            return 'application/octet-stream'
        raise ValueError('Unsupported image type given')


def _get_extension_for_mime_type(mime_type: str) -> str:
    if mime_type == 'image/png':
        return 'png'
    elif mime_type == 'image/jpeg':
        return 'jpg'
    elif mime_type == 'image/gif':
        return 'gif'
    elif mime_type == 'video/mp4':
        return 'mp4'
    else:
        return 'webp'


def _bytes_to_base64_data(data: bytes) -> str:
    fmt = 'data:{mime};base64,{data}'
    mime = _get_mime_type_for_image(data, fallback=True)
    b64 = b64encode(data).decode('ascii')
    return fmt.format(mime=mime, data=b64)


def _base64_to_bytes(data: str) -> bytes:
    return b64decode(data.encode('ascii'))


def _is_submodule(parent: str, child: str) -> bool:
    return parent == child or child.startswith(parent + '.')


def _handle_metadata(obj):
    try:
        return dict(obj)
    except Exception:
        raise TypeError(f'Type {obj.__class__.__name__} is not JSON serializable')


if HAS_ORJSON:

    def _to_json(obj: Any) -> str:
        return orjson.dumps(obj, default=_handle_metadata).decode('utf-8')

    _from_json = orjson.loads

else:

    def _to_json(obj: Any) -> str:
        return json.dumps(obj, separators=(',', ':'), ensure_ascii=True, default=_handle_metadata)

    _from_json = json.loads


def _parse_ratelimit_header(request: Any, *, use_clock: bool = False) -> float:
    reset_after: Optional[str] = request.headers.get('X-Ratelimit-Reset-After')
    if use_clock or not reset_after:
        utc = datetime.timezone.utc
        now = datetime.datetime.now(utc)
        reset = datetime.datetime.fromtimestamp(float(request.headers['X-Ratelimit-Reset']), utc)
        return (reset - now).total_seconds()
    else:
        return float(reset_after)


async def maybe_coroutine(f: MaybeAwaitableFunc[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    r"""|coro|

    A helper function that will await the result of a function if it's a coroutine
    or return the result if it's not.

    This is useful for functions that may or may not be coroutines.

    .. versionadded:: 2.0

    Parameters
    -----------
    f: Callable[..., Any]
        The function or coroutine to call.
    \*args
        The arguments to pass to the function.
    \*\*kwargs
        The keyword arguments to pass to the function.

    Returns
    --------
    Any
        The result of the function or coroutine.
    """

    value = f(*args, **kwargs)
    if _isawaitable(value):
        return await value
    else:
        return value


async def async_all(
    gen: Iterable[Union[T, Awaitable[T]]],
    *,
    check: Callable[[Union[T, Awaitable[T]]], TypeGuard[Awaitable[T]]] = _isawaitable,  # type: ignore
) -> bool:
    for elem in gen:
        if check(elem):
            elem = await elem
        if not elem:
            return False
    return True


async def sane_wait_for(futures: Iterable[Awaitable[T]], *, timeout: Optional[float]) -> Set[asyncio.Task[T]]:
    ensured = [asyncio.ensure_future(fut) for fut in futures]
    done, pending = await asyncio.wait(ensured, timeout=timeout, return_when=asyncio.ALL_COMPLETED)

    if len(pending) != 0:
        raise asyncio.TimeoutError()

    return done


def get_slots(cls: Type[Any]) -> Iterator[str]:
    for mro in reversed(cls.__mro__):
        try:
            yield from mro.__slots__
        except AttributeError:
            continue


def compute_timedelta(dt: datetime.datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.astimezone()
    now = datetime.datetime.now(datetime.timezone.utc)
    return max((dt - now).total_seconds(), 0)


@overload
async def sleep_until(when: datetime.datetime, result: T) -> T:
    ...


@overload
async def sleep_until(when: datetime.datetime) -> None:
    ...


async def sleep_until(when: datetime.datetime, result: Optional[T] = None) -> Optional[T]:
    """|coro|

    Sleep until a specified time.

    If the time supplied is in the past this function will yield instantly.

    .. versionadded:: 1.3

    Parameters
    -----------
    when: :class:`datetime.datetime`
        The timestamp in which to sleep until. If the datetime is naive then
        it is assumed to be local time.
    result: Any
        If provided is returned to the caller when the coroutine completes.
    """
    delta = compute_timedelta(when)
    return await asyncio.sleep(delta, result)


def utcnow() -> datetime.datetime:
    """A helper function to return an aware UTC datetime representing the current time.

    This should be preferred to :meth:`datetime.datetime.utcnow` since it is an aware
    datetime, compared to the naive datetime in the standard library.

    .. versionadded:: 2.0

    Returns
    --------
    :class:`datetime.datetime`
        The current aware datetime in UTC.
    """
    return datetime.datetime.now(datetime.timezone.utc)


def valid_icon_size(size: int) -> bool:
    """Icons must be power of 2 within [16, 4096]."""
    ADDITIONAL_SIZES = (20, 22, 24, 28, 40, 44, 48, 56, 60, 80, 96, 100, 160, 240, 300, 320, 480, 600, 640, 1280, 1536, 3072)
    return (not size & (size - 1) and 4096 >= size >= 16) or size in ADDITIONAL_SIZES


class SnowflakeList(_SnowflakeListBase):
    """Internal data storage class to efficiently store a list of snowflakes.

    This should have the following characteristics:

    - Low memory usage
    - O(n) iteration (obviously)
    - O(n log n) initial creation if data is unsorted
    - O(log n) search and indexing
    - O(n) insertion
    """

    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(self, data: Optional[Iterable[int]] = None, *, is_sorted: bool = False):
            ...

    def __new__(cls, data: Optional[Iterable[int]] = None, *, is_sorted: bool = False) -> Self:
        if data:
            return array.array.__new__(cls, 'Q', data if is_sorted else sorted(data))  # type: ignore
        return array.array.__new__(cls, 'Q')  # type: ignore

    def __contains__(self, element: int) -> bool:
        return self.has(element)

    def add(self, element: int) -> None:
        i = bisect_left(self, element)
        self.insert(i, element)

    def get(self, element: int) -> Optional[int]:
        i = bisect_left(self, element)
        return self[i] if i != len(self) and self[i] == element else None

    def has(self, element: int) -> bool:
        i = bisect_left(self, element)
        return i != len(self) and self[i] == element


_IS_ASCII = re.compile(r'^[\x00-\x7f]+$')


def _string_width(string: str, *, _IS_ASCII=_IS_ASCII) -> int:
    """Returns string's width."""
    match = _IS_ASCII.match(string)
    if match:
        return match.endpos

    UNICODE_WIDE_CHAR_TYPE = 'WFA'
    func = unicodedata.east_asian_width
    return sum(2 if func(char) in UNICODE_WIDE_CHAR_TYPE else 1 for char in string)


class ResolvedInvite(NamedTuple):
    code: str
    event: Optional[int]


def resolve_invite(invite: Union[Invite, str]) -> ResolvedInvite:
    """Resolves an invite from a :class:`~discord.Invite`, URL or code.

    .. versionchanged:: 2.0
        Now returns a :class:`.ResolvedInvite` instead of a
        :class:`str`.

    Parameters
    -----------
    invite: Union[:class:`~discord.Invite`, :class:`str`]
        The invite.

    Raises
    -------
    ValueError
        The invite is not a valid Discord invite, e.g. is not a URL
        or does not contain alphanumeric characters.

    Returns
    --------
    :class:`.ResolvedInvite`
        A data class containing the invite code and the event ID.
    """
    from .invite import Invite  # Circular import

    if isinstance(invite, Invite):
        return ResolvedInvite(invite.code, invite.scheduled_event_id)
    else:
        rx = r'(?:https?\:\/\/)?discord(?:\.gg|(?:app)?\.com\/invite)\/[^/]+'
        m = re.match(rx, invite)

        if m:
            url = yarl.URL(invite)
            code = url.parts[-1]
            event_id = url.query.get('event')

            return ResolvedInvite(code, int(event_id) if event_id else None)

        allowed_characters = r'[a-zA-Z0-9\-_]+'
        if not re.fullmatch(allowed_characters, invite):
            raise ValueError('Invite contains characters that are not allowed')

        return ResolvedInvite(invite, None)


def resolve_template(code: Union[Template, str]) -> str:
    """
    Resolves a template code from a :class:`~discord.Template`, URL or code.

    .. versionadded:: 1.4

    Parameters
    -----------
    code: Union[:class:`~discord.Template`, :class:`str`]
        The code.

    Returns
    --------
    :class:`str`
        The template code.
    """
    from .template import Template  # Circular import

    if isinstance(code, Template):
        return code.code
    else:
        rx = r'(?:https?\:\/\/)?discord(?:\.new|(?:app)?\.com\/template)\/(.+)'
        m = re.match(rx, code)
        if m:
            return m.group(1)
    return code


def resolve_gift(code: Union[Gift, str]) -> str:
    """
    Resolves a gift code from a :class:`~discord.Gift`, URL or code.

    .. versionadded:: 2.0

    Parameters
    -----------
    code: Union[:class:`~discord.Gift`, :class:`str`]
        The code.

    Returns
    --------
    :class:`str`
        The gift code.
    """
    from .entitlements import Gift  # Circular import

    if isinstance(code, Gift):
        return code.code
    else:
        rx = r'(?:https?\:\/\/)?(?:discord(?:app)?\.com\/(?:gifts|billing\/promotions)|promos\.discord\.gg|discord.gift)\/(.+)'
        m = re.match(rx, code)
        if m:
            return m.group(1)
    return code


_MARKDOWN_ESCAPE_SUBREGEX = '|'.join(r'\{0}(?=([\s\S]*((?<!\{0})\{0})))'.format(c) for c in ('*', '`', '_', '~', '|'))

_MARKDOWN_ESCAPE_COMMON = r'^>(?:>>)?\s|\[.+\]\(.+\)|^#{1,3}|^\s*-'

_MARKDOWN_ESCAPE_REGEX = re.compile(fr'(?P<markdown>{_MARKDOWN_ESCAPE_SUBREGEX}|{_MARKDOWN_ESCAPE_COMMON})', re.MULTILINE)

_URL_REGEX = r'(?P<url><[^: >]+:\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,:;\"\'\]\s])'

_MARKDOWN_STOCK_REGEX = fr'(?P<markdown>[_\\~|\*`]|{_MARKDOWN_ESCAPE_COMMON})'


def remove_markdown(text: str, *, ignore_links: bool = True) -> str:
    """A helper function that removes markdown characters.

    .. versionadded:: 1.7

    .. note::
            This function is not markdown aware and may remove meaning from the original text. For example,
            if the input contains ``10 * 5`` then it will be converted into ``10  5``.

    Parameters
    -----------
    text: :class:`str`
        The text to remove markdown from.
    ignore_links: :class:`bool`
        Whether to leave links alone when removing markdown. For example,
        if a URL in the text contains characters such as ``_`` then it will
        be left alone. Defaults to ``True``.

    Returns
    --------
    :class:`str`
        The text with the markdown special characters removed.
    """

    def replacement(match: re.Match[str]) -> str:
        groupdict = match.groupdict()
        return groupdict.get('url', '')

    regex = _MARKDOWN_STOCK_REGEX
    if ignore_links:
        regex = f'(?:{_URL_REGEX}|{regex})'
    return re.sub(regex, replacement, text, 0, re.MULTILINE)


def escape_markdown(text: str, *, as_needed: bool = False, ignore_links: bool = True) -> str:
    r"""A helper function that escapes Discord's markdown.

    Parameters
    -----------
    text: :class:`str`
        The text to escape markdown from.
    as_needed: :class:`bool`
        Whether to escape the markdown characters as needed. This
        means that it does not escape extraneous characters if it's
        not necessary, e.g. ``**hello**`` is escaped into ``\*\*hello**``
        instead of ``\*\*hello\*\*``. Note however that this can open
        you up to some clever syntax abuse. Defaults to ``False``.
    ignore_links: :class:`bool`
        Whether to leave links alone when escaping markdown. For example,
        if a URL in the text contains characters such as ``_`` then it will
        be left alone. This option is not supported with ``as_needed``.
        Defaults to ``True``.

    Returns
    --------
    :class:`str`
        The text with the markdown special characters escaped with a slash.
    """

    if not as_needed:

        def replacement(match):
            groupdict = match.groupdict()
            is_url = groupdict.get('url')
            if is_url:
                return is_url
            return '\\' + groupdict['markdown']

        regex = _MARKDOWN_STOCK_REGEX
        if ignore_links:
            regex = f'(?:{_URL_REGEX}|{regex})'
        return re.sub(regex, replacement, text, 0, re.MULTILINE)
    else:
        text = re.sub(r'\\', r'\\\\', text)
        return _MARKDOWN_ESCAPE_REGEX.sub(r'\\\1', text)


def escape_mentions(text: str) -> str:
    """A helper function that escapes everyone, here, role, and user mentions.

    .. note::

        This does not include channel mentions.

    .. note::

        For more granular control over what mentions should be escaped
        within messages, refer to the :class:`~discord.AllowedMentions`
        class.

    Parameters
    -----------
    text: :class:`str`
        The text to escape mentions from.

    Returns
    --------
    :class:`str`
        The text with the mentions removed.
    """
    return re.sub(r'@(everyone|here|[!&]?[0-9]{17,20})', '@\u200b\\1', text)


def _chunk(iterator: Iterable[T], max_size: int) -> Iterator[List[T]]:
    ret = []
    n = 0
    for item in iterator:
        ret.append(item)
        n += 1
        if n == max_size:
            yield ret
            ret = []
            n = 0
    if ret:
        yield ret


async def _achunk(iterator: AsyncIterable[T], max_size: int) -> AsyncIterator[List[T]]:
    ret = []
    n = 0
    async for item in iterator:
        ret.append(item)
        n += 1
        if n == max_size:
            yield ret
            ret = []
            n = 0
    if ret:
        yield ret


@overload
def as_chunks(iterator: AsyncIterable[T], max_size: int) -> AsyncIterator[List[T]]:
    ...


@overload
def as_chunks(iterator: Iterable[T], max_size: int) -> Iterator[List[T]]:
    ...


def as_chunks(iterator: _Iter[T], max_size: int) -> _Iter[List[T]]:
    """A helper function that collects an iterator into chunks of a given size.

    .. versionadded:: 2.0

    Parameters
    ----------
    iterator: Union[:class:`collections.abc.Iterable`, :class:`collections.abc.AsyncIterable`]
        The iterator to chunk, can be sync or async.
    max_size: :class:`int`
        The maximum chunk size.


    .. warning::

        The last chunk collected may not be as large as ``max_size``.

    Returns
    --------
    Union[:class:`Iterator`, :class:`AsyncIterator`]
        A new iterator which yields chunks of a given size.
    """
    if max_size <= 0:
        raise ValueError('Chunk sizes must be greater than 0.')

    if isinstance(iterator, AsyncIterable):
        return _achunk(iterator, max_size)
    return _chunk(iterator, max_size)


PY_310 = sys.version_info >= (3, 10)
PY_312 = sys.version_info >= (3, 12)


def flatten_literal_params(parameters: Iterable[Any]) -> Tuple[Any, ...]:
    params = []
    literal_cls = type(Literal[0])
    for p in parameters:
        if isinstance(p, literal_cls):
            params.extend(p.__args__)  # type: ignore
        else:
            params.append(p)
    return tuple(params)


def normalise_optional_params(parameters: Iterable[Any]) -> Tuple[Any, ...]:
    none_cls = type(None)
    return tuple(p for p in parameters if p is not none_cls) + (none_cls,)


def evaluate_annotation(
    tp: Any,
    globals: Dict[str, Any],
    locals: Dict[str, Any],
    cache: Dict[str, Any],
    *,
    implicit_str: bool = True,
) -> Any:
    if isinstance(tp, ForwardRef):
        tp = tp.__forward_arg__
        # ForwardRefs always evaluate their internals
        implicit_str = True

    if implicit_str and isinstance(tp, str):
        if tp in cache:
            return cache[tp]
        evaluated = evaluate_annotation(eval(tp, globals, locals), globals, locals, cache)
        cache[tp] = evaluated
        return evaluated

    if PY_312 and getattr(tp.__repr__, '__objclass__', None) is typing.TypeAliasType:  # type: ignore
        temp_locals = dict(**locals, **{t.__name__: t for t in tp.__type_params__})
        annotation = evaluate_annotation(tp.__value__, globals, temp_locals, cache.copy())
        if hasattr(tp, '__args__'):
            annotation = annotation[tp.__args__]
        return annotation

    if hasattr(tp, '__supertype__'):
        return evaluate_annotation(tp.__supertype__, globals, locals, cache)

    if hasattr(tp, '__metadata__'):
        # Annotated[X, Y] can access Y via __metadata__
        metadata = tp.__metadata__[0]
        return evaluate_annotation(metadata, globals, locals, cache)

    if hasattr(tp, '__args__'):
        implicit_str = True
        is_literal = False
        args = tp.__args__
        if not hasattr(tp, '__origin__'):
            if PY_310 and tp.__class__ is types.UnionType:  # type: ignore
                converted = Union[args]
                return evaluate_annotation(converted, globals, locals, cache)

            return tp
        if tp.__origin__ is Union:
            try:
                if args.index(type(None)) != len(args) - 1:
                    args = normalise_optional_params(tp.__args__)
            except ValueError:
                pass
        if tp.__origin__ is Literal:
            if not PY_310:
                args = flatten_literal_params(tp.__args__)
            implicit_str = False
            is_literal = True

        evaluated_args = tuple(evaluate_annotation(arg, globals, locals, cache, implicit_str=implicit_str) for arg in args)

        if is_literal and not all(isinstance(x, (str, int, bool, type(None))) for x in evaluated_args):
            raise TypeError('Literal arguments must be of type str, int, bool, or NoneType.')

        try:
            return tp.copy_with(evaluated_args)
        except AttributeError:
            return tp.__origin__[evaluated_args]

    return tp


def resolve_annotation(
    annotation: Any,
    globalns: Dict[str, Any],
    localns: Optional[Dict[str, Any]],
    cache: Optional[Dict[str, Any]],
) -> Any:
    if annotation is None:
        return type(None)
    if isinstance(annotation, str):
        annotation = ForwardRef(annotation)

    locals = globalns if localns is None else localns
    if cache is None:
        cache = {}
    return evaluate_annotation(annotation, globalns, locals, cache)


def is_inside_class(func: Callable[..., Any]) -> bool:
    # For methods defined in a class, the qualname has a dotted path
    # denoting which class it belongs to. So, e.g. for A.foo the qualname
    # would be A.foo while a global foo() would just be foo.
    #
    # Unfortunately, for nested functions this breaks. So inside an outer
    # function named outer, those two would end up having a qualname with
    # outer.<locals>.A.foo and outer.<locals>.foo

    if func.__qualname__ == func.__name__:
        return False
    (remaining, _, _) = func.__qualname__.rpartition('.')
    return not remaining.endswith('<locals>')


TimestampStyle = Literal['f', 'F', 'd', 'D', 't', 'T', 'R']


def format_dt(dt: datetime.datetime, /, style: Optional[TimestampStyle] = None) -> str:
    """A helper function to format a :class:`datetime.datetime` for presentation within Discord.

    This allows for a locale-independent way of presenting data using Discord specific Markdown.

    +-------------+----------------------------+-----------------+
    |    Style    |       Example Output       |   Description   |
    +=============+============================+=================+
    | t           | 22:57                      | Short Time      |
    +-------------+----------------------------+-----------------+
    | T           | 22:57:58                   | Long Time       |
    +-------------+----------------------------+-----------------+
    | d           | 17/05/2016                 | Short Date      |
    +-------------+----------------------------+-----------------+
    | D           | 17 May 2016                | Long Date       |
    +-------------+----------------------------+-----------------+
    | f (default) | 17 May 2016 22:57          | Short Date Time |
    +-------------+----------------------------+-----------------+
    | F           | Tuesday, 17 May 2016 22:57 | Long Date Time  |
    +-------------+----------------------------+-----------------+
    | R           | 5 years ago                | Relative Time   |
    +-------------+----------------------------+-----------------+

    Note that the exact output depends on the user's locale setting in the client. The example output
    presented is using the ``en-GB`` locale.

    .. versionadded:: 2.0

    Parameters
    -----------
    dt: :class:`datetime.datetime`
        The datetime to format.
    style: :class:`str`
        The style to format the datetime with.

    Returns
    --------
    :class:`str`
        The formatted string.
    """
    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'


@deprecated()
def set_target(
    items: Iterable[ApplicationCommand],
    *,
    channel: Optional[Messageable] = MISSING,
    message: Optional[Message] = MISSING,
    user: Optional[Snowflake] = MISSING,
) -> None:
    """A helper function to set the target for a list of items.

    This is used to set the target for a list of application commands.

    Suppresses all AttributeErrors so you can pass multiple types of commands and
    not worry about which elements support which parameter.

    .. versionadded:: 2.0

    .. deprecated:: 2.1

    Parameters
    -----------
    items: Iterable[:class:`.abc.ApplicationCommand`]
        A list of items to set the target for.
    channel: Optional[:class:`.abc.Messageable`]
        The channel to target.
    message: Optional[:class:`.Message`]
        The message to target.
    user: Optional[:class:`~discord.abc.Snowflake`]
        The user to target.
    """
    attrs = {}
    if channel is not MISSING:
        attrs['target_channel'] = channel
    if message is not MISSING:
        attrs['target_message'] = message
    if user is not MISSING:
        attrs['target_user'] = user

    for item in items:
        for k, v in attrs.items():
            try:
                setattr(item, k, v)
            except AttributeError:
                pass


def _generate_session_id() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


def _generate_nonce() -> str:
    return str(time_snowflake(utcnow()))


def _parse_localizations(data: Any, key: str) -> tuple[Any, dict]:
    values = data.get(key)
    values = values if isinstance(values, dict) else {'default': values}
    string = values['default']
    localizations = {
        try_enum(Locale, k): v for k, v in (values.get('localizations', data.get(f'{key}_localizations')) or {}).items()
    }
    return string, localizations


class ExpiringString(collections.UserString):
    def __init__(self, data: str, timeout: int) -> None:
        super().__init__(data)
        self._timer: Timer = Timer(timeout, self._destruct)
        self._timer.start()

    def _update(self, data: str, timeout: int) -> None:
        try:
            self._timer.cancel()
        except:
            pass
        self.data = data
        self._timer: Timer = Timer(timeout, self._destruct)
        self._timer.start()

    def _destruct(self) -> None:
        self.data = ''

    def destroy(self) -> None:
        self._destruct()
        self._timer.cancel()


def is_docker() -> bool:
    path = '/proc/self/cgroup'
    return os.path.exists('/.dockerenv') or (os.path.isfile(path) and any('docker' in line for line in open(path)))


def stream_supports_colour(stream: Any) -> bool:
    is_a_tty = hasattr(stream, 'isatty') and stream.isatty()

    # Pycharm and Vscode support colour in their inbuilt editors
    if 'PYCHARM_HOSTED' in os.environ or os.environ.get('TERM_PROGRAM') == 'vscode':
        return is_a_tty

    if sys.platform != 'win32':
        # Docker does not consistently have a tty attached to it
        return is_a_tty or is_docker()

    # ANSICON checks for things like ConEmu
    # WT_SESSION checks if this is Windows Terminal
    return is_a_tty and ('ANSICON' in os.environ or 'WT_SESSION' in os.environ)


class _ColourFormatter(logging.Formatter):
    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: logging.Formatter(
            f'\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


def setup_logging(
    *,
    handler: logging.Handler = MISSING,
    formatter: logging.Formatter = MISSING,
    level: int = MISSING,
    root: bool = True,
) -> None:
    """A helper function to setup logging.

    This is superficially similar to :func:`logging.basicConfig` but
    uses different defaults and a colour formatter if the stream can
    display colour.

    This is used by the :class:`~discord.Client` to set up logging
    if ``log_handler`` is not ``None``.

    .. versionadded:: 2.0

    Parameters
    -----------
    handler: :class:`logging.Handler`
        The log handler to use for the library's logger.

        The default log handler if not provided is :class:`logging.StreamHandler`.
    formatter: :class:`logging.Formatter`
        The formatter to use with the given log handler. If not provided then it
        defaults to a colour based logging formatter (if available). If colour
        is not available then a simple logging formatter is provided.
    level: :class:`int`
        The default log level for the library's logger. Defaults to ``logging.INFO``.
    root: :class:`bool`
        Whether to set up the root logger rather than the library logger.
        Unlike the default for :class:`~discord.Client`, this defaults to ``True``.
    """

    if level is MISSING:
        level = logging.INFO

    if handler is MISSING:
        handler = logging.StreamHandler()

    if formatter is MISSING:
        if isinstance(handler, logging.StreamHandler) and stream_supports_colour(handler.stream):
            formatter = _ColourFormatter()
        else:
            dt_fmt = '%Y-%m-%d %H:%M:%S'
            formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

    if root:
        logger = logging.getLogger()
    else:
        library, _, _ = __name__.partition('.')
        logger = logging.getLogger(library)

    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)


if TYPE_CHECKING:

    def murmurhash32(key: Union[bytes, bytearray, memoryview, str], seed: int = 0, *, signed: bool = True) -> int:  # type: ignore
        pass

else:
    try:
        from mmh3 import hash as murmurhash32  # Prefer the mmh3 package if available

    except ImportError:
        # Modified murmurhash3 function from https://github.com/wc-duck/pymmh3/blob/master/pymmh3.py
        def murmurhash32(key: Union[bytes, bytearray, memoryview, str], seed: int = 0, *, signed: bool = True) -> int:
            key = bytearray(key.encode() if isinstance(key, str) else key)
            length = len(key)
            nblocks = int(length / 4)

            h1 = seed
            c1 = 0xCC9E2D51
            c2 = 0x1B873593

            for block_start in range(0, nblocks * 4, 4):
                k1 = (
                    key[block_start + 3] << 24
                    | key[block_start + 2] << 16
                    | key[block_start + 1] << 8
                    | key[block_start + 0]
                )

                k1 = (c1 * k1) & 0xFFFFFFFF
                k1 = (k1 << 15 | k1 >> 17) & 0xFFFFFFFF
                k1 = (c2 * k1) & 0xFFFFFFFF

                h1 ^= k1
                h1 = (h1 << 13 | h1 >> 19) & 0xFFFFFFFF
                h1 = (h1 * 5 + 0xE6546B64) & 0xFFFFFFFF

            tail_index = nblocks * 4
            k1 = 0
            tail_size = length & 3

            if tail_size >= 3:
                k1 ^= key[tail_index + 2] << 16
            if tail_size >= 2:
                k1 ^= key[tail_index + 1] << 8
            if tail_size >= 1:
                k1 ^= key[tail_index + 0]
            if tail_size > 0:
                k1 = (k1 * c1) & 0xFFFFFFFF
                k1 = (k1 << 15 | k1 >> 17) & 0xFFFFFFFF
                k1 = (k1 * c2) & 0xFFFFFFFF
                h1 ^= k1

            unsigned_val = h1 ^ length
            unsigned_val ^= unsigned_val >> 16
            unsigned_val = (unsigned_val * 0x85EBCA6B) & 0xFFFFFFFF
            unsigned_val ^= unsigned_val >> 13
            unsigned_val = (unsigned_val * 0xC2B2AE35) & 0xFFFFFFFF
            unsigned_val ^= unsigned_val >> 16
            if not signed or (unsigned_val & 0x80000000 == 0):
                return unsigned_val
            else:
                return -((unsigned_val ^ 0xFFFFFFFF) + 1)


_SENTRY_ASSET_REGEX = re.compile(r'assets/(sentry\.\w+)\.js')
_BUILD_NUMBER_REGEX = re.compile(r'buildNumber\D+(\d+)"')


class Headers:
    """A class to provide standard headers for HTTP requests.

    For now, this is NOT user-customizable and always emulates Chrome on Windows.
    """

    FALLBACK_BUILD_NUMBER = 9999
    FALLBACK_BROWSER_VERSION = 136

    def __init__(
        self,
        *,
        platform: Literal['Windows', 'macOS', 'Linux', 'Android', 'iOS'],
        major_version: int,
        super_properties: Dict[str, Any],
        encoded_super_properties: str,
        extra_gateway_properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.platform = platform
        self.major_version = major_version
        self.super_properties = super_properties
        self.encoded_super_properties = encoded_super_properties
        self.extra_gateway_properties = extra_gateway_properties or {}

    @classmethod
    async def default(
        cls: type[Self], session: ClientSession, proxy: Optional[str] = None, proxy_auth: Optional[BasicAuth] = None
    ) -> Self:
        """Creates a new :class:`Headers` instance using the default fetching mechanisms."""
        try:
            properties, extra, encoded = await asyncio.wait_for(
                cls.get_api_properties(session, 'web', proxy=proxy, proxy_auth=proxy_auth), timeout=3
            )
        except Exception:
            _log.info('Info API temporarily down. Falling back to manual retrieval...')
        else:
            return cls(
                platform='Windows',
                major_version=int(properties['browser_version'].split('.')[0]),
                super_properties=properties,
                encoded_super_properties=encoded,
                extra_gateway_properties=extra,
            )

        try:
            bn = await cls._get_build_number(session, proxy=proxy, proxy_auth=proxy_auth)
        except Exception:
            _log.critical('Could not retrieve client build number. Falling back to hardcoded value...')
            bn = cls.FALLBACK_BUILD_NUMBER

        try:
            bv = await cls._get_browser_version(session, proxy=proxy, proxy_auth=proxy_auth)
        except Exception:
            _log.critical('Could not retrieve browser version. Falling back to hardcoded value...')
            bv = cls.FALLBACK_BROWSER_VERSION

        properties = {
            'os': 'Windows',
            'browser': 'Chrome',
            'device': '',
            'system_locale': 'en-US',
            'browser_user_agent': cls._get_user_agent(bv),
            'browser_version': f'{bv}.0.0.0',
            'os_version': '10',
            'referrer': '',
            'referring_domain': '',
            'referrer_current': '',
            'referring_domain_current': '',
            'release_channel': 'stable',
            'client_build_number': bn,
            'client_event_source': None,
            'has_client_mods': False,
            'client_launch_id': str(uuid.uuid4()),
            'client_app_state': 'unfocused',
            'client_heartbeat_session_id': str(uuid.uuid4()),
        }

        return cls(
            platform='Windows',
            major_version=bv,
            super_properties=properties,
            encoded_super_properties=b64encode(_to_json(properties).encode()).decode('utf-8'),
            extra_gateway_properties={
                'is_fast_connect': False,
                'latest_headless_tasks': [],
                'latest_headless_task_run_seconds_before': None,
                'gateway_connect_reasons': 'AppSkeleton',
            },
        )

    @cached_property
    def user_agent(self) -> str:
        """Returns the user agent to be used for HTTP requests."""
        return self.super_properties['browser_user_agent']

    @cached_property
    def client_hints(self) -> Dict[str, str]:
        """Returns the client hints to be used for HTTP requests."""
        return {
            'Sec-CH-UA': ', '.join([f'"{brand}";v="{version}"' for brand, version in self.generate_brand_version_list()]),
            'Sec-CH-UA-Mobile': '?1' if self.platform in ('Android', 'iOS') else '?0',
            'Sec-CH-UA-Platform': f'"{self.platform}"',
        }

    @property
    def gateway_properties(self) -> Dict[str, Any]:
        """Returns the properties to be used for the Gateway."""
        return {
            **self.super_properties,
            **self.extra_gateway_properties,
        }

    @staticmethod
    async def get_api_properties(
        session: ClientSession, type: str, *, proxy: Optional[str] = None, proxy_auth: Optional[BasicAuth] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
        """Fetches client properties from the API."""
        async with session.post(
            f'https://cordapi.dolfi.es/api/v2/properties/{type}', proxy=proxy, proxy_auth=proxy_auth
        ) as resp:
            resp.raise_for_status()
            json = await resp.json()
            return json['properties'], json['extra_gateway_properties'], json['encoded']

    @staticmethod
    async def _get_build_number(
        session: ClientSession, *, proxy: Optional[str] = None, proxy_auth: Optional[BasicAuth] = None
    ) -> int:
        """Fetches client build number."""
        async with session.get('https://discord.com/login', proxy=proxy, proxy_auth=proxy_auth) as resp:
            app = await resp.text()
            match = _SENTRY_ASSET_REGEX.search(app)
            if match is None:
                raise RuntimeError('Could not find sentry asset file')
            sentry = match.group(1)

        async with session.get(f'https://static.discord.com/assets/{sentry}.js', proxy=proxy, proxy_auth=proxy_auth) as resp:
            build = await resp.text()
            match = _BUILD_NUMBER_REGEX.search(build)
            if match is None:
                raise RuntimeError('Could not find build number')
            return int(match.group(1))

    @staticmethod
    async def _get_browser_version(
        session: ClientSession, proxy: Optional[str] = None, proxy_auth: Optional[BasicAuth] = None
    ) -> int:
        """Fetches the latest Windows 10/Chrome major browser version."""
        async with session.get(
            'https://versionhistory.googleapis.com/v1/chrome/platforms/win/channels/stable/versions',
            proxy=proxy,
            proxy_auth=proxy_auth,
        ) as response:
            data = await response.json()
            return int(data['versions'][0]['version'].split('.')[0])

    @staticmethod
    def _get_user_agent(version: int, brand: Optional[str] = None) -> str:
        """Fetches the latest Windows/Chrome user-agent."""
        # Because of [user agent reduction](https://www.chromium.org/updates/ua-reduction/), we just need the major version now :)
        ret = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36'
        if brand:
            # e.g. Edg/v.0.0.0 for Microsoft Edge
            ret += f' {brand}/{version}.0.0.0'
        return ret

    # These are all adapted from Chromium source code (https://github.com/chromium/chromium/blob/master/components/embedder_support/user_agent_utils.cc)

    def generate_brand_version_list(self, brand: Optional[str] = "Google Chrome") -> List[Tuple[str, str]]:
        """Generates a list of brand and version pairs for the user-agent."""
        version = self.major_version
        greasey_bv = self._get_greased_user_agent_brand_version(version)
        chromium_bv = ("Chromium", version)
        brand_version_list = [greasey_bv, chromium_bv]
        if brand:
            brand_version_list.append((brand, version))

        order = self._get_random_order(version, len(brand_version_list))
        shuffled_brand_version_list: List[Any] = [None] * len(brand_version_list)
        for i, idx in enumerate(order):
            shuffled_brand_version_list[idx] = brand_version_list[i]
        return shuffled_brand_version_list

    @staticmethod
    def _get_random_order(seed: int, size: int) -> List[int]:
        random.seed(seed)
        if size == 2:
            return [seed % size, (seed + 1) % size]
        elif size == 3:
            orders = [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]]
            return orders[seed % len(orders)]
        else:
            orders = [
                [0, 1, 2, 3],
                [0, 1, 3, 2],
                [0, 2, 1, 3],
                [0, 2, 3, 1],
                [0, 3, 1, 2],
                [0, 3, 2, 1],
                [1, 0, 2, 3],
                [1, 0, 3, 2],
                [1, 2, 0, 3],
                [1, 2, 3, 0],
                [1, 3, 0, 2],
                [1, 3, 2, 0],
                [2, 0, 1, 3],
                [2, 0, 3, 1],
                [2, 1, 0, 3],
                [2, 1, 3, 0],
                [2, 3, 0, 1],
                [2, 3, 1, 0],
                [3, 0, 1, 2],
                [3, 0, 2, 1],
                [3, 1, 0, 2],
                [3, 1, 2, 0],
                [3, 2, 0, 1],
                [3, 2, 1, 0],
            ]
            return orders[seed % len(orders)]

    @staticmethod
    def _get_greased_user_agent_brand_version(seed: int) -> Tuple[str, str]:
        greasey_chars = [" ", "(", ":", "-", ".", "/", ")", ";", "=", "?", "_"]
        greased_versions = ["8", "99", "24"]
        greasey_brand = (
            f"Not{greasey_chars[seed % len(greasey_chars)]}A{greasey_chars[(seed + 1) % len(greasey_chars)]}Brand"
        )
        greasey_version = greased_versions[seed % len(greased_versions)]

        version_parts = greasey_version.split('.')
        if len(version_parts) > 1:
            greasey_major_version = version_parts[0]
        else:
            greasey_major_version = greasey_version
        return (greasey_brand, greasey_major_version)


class IDGenerator:
    def __init__(self):
        self.prefix = random.randint(0, 0xFFFFFFFF) & 0xFFFFFFFF
        self.creation_time = int(time.time() * 1000)
        self.sequence = 0

    def generate(self, user_id: int = 0):
        uuid = bytearray(24)
        # Lowest signed 32 bits
        struct.pack_into("<I", uuid, 0, user_id & 0xFFFFFFFF)
        struct.pack_into("<I", uuid, 4, user_id >> 32)
        struct.pack_into("<I", uuid, 8, self.prefix)
        # Lowest signed 32 bits
        struct.pack_into("<I", uuid, 12, self.creation_time & 0xFFFFFFFF)
        struct.pack_into("<I", uuid, 16, self.creation_time >> 32)
        struct.pack_into("<I", uuid, 20, self.sequence)
        self.sequence += 1
        return b64encode(uuid).decode("utf-8")


if HAS_ZSTD:

    class _ZstdDecompressionContext:
        __slots__ = ('context',)

        COMPRESSION_TYPE: str = 'zstd-stream'

        def __init__(self) -> None:
            decompressor = zstandard.ZstdDecompressor()
            self.context = decompressor.decompressobj()

        def decompress(self, data: bytes, /) -> str | None:
            # Each WS message is a complete gateway message
            return self.context.decompress(data).decode('utf-8')

    _ActiveDecompressionContext: Type[_DecompressionContext] = _ZstdDecompressionContext
else:

    class _ZlibDecompressionContext:
        __slots__ = ('context', 'buffer')

        COMPRESSION_TYPE: str = 'zlib-stream'

        def __init__(self) -> None:
            self.buffer: bytearray = bytearray()
            self.context = zlib.decompressobj()

        def decompress(self, data: bytes, /) -> str | None:
            self.buffer.extend(data)

            # Check whether ending is Z_SYNC_FLUSH
            if len(data) < 4 or data[-4:] != b'\x00\x00\xff\xff':
                return

            msg = self.context.decompress(self.buffer)
            self.buffer = bytearray()

            return msg.decode('utf-8')

    _ActiveDecompressionContext: Type[_DecompressionContext] = _ZlibDecompressionContext
