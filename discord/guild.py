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

import copy
from datetime import datetime
from operator import attrgetter
import unicodedata
from typing import (
    Any,
    AsyncIterator,
    ClassVar,
    Collection,
    Coroutine,
    Dict,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Sequence,
    Set,
    Literal,
    Optional,
    TYPE_CHECKING,
    Tuple,
    Union,
    overload,
)
import warnings

from . import utils, abc
from .role import Role
from .member import Member, VoiceState
from .emoji import Emoji
from .errors import ClientException, InvalidData
from .permissions import Permissions, PermissionOverwrite
from .colour import Colour
from .errors import ClientException
from .channel import *
from .channel import _guild_channel_factory, _threaded_guild_channel_factory
from .enums import (
    AuditLogAction,
    VideoQualityMode,
    ChannelType,
    EntityType,
    HubType,
    PrivacyLevel,
    try_enum,
    VerificationLevel,
    ContentFilter,
    NotificationLevel,
    NSFWLevel,
    MFALevel,
    Locale,
    AutoModRuleEventType,
    ForumOrderType,
    ForumLayoutType,
    ReadStateType,
)
from .mixins import Hashable
from .user import User
from .invite import Invite
from .widget import Widget
from .asset import Asset
from .flags import SystemChannelFlags
from .integrations import Integration, _integration_factory
from .scheduled_event import ScheduledEvent
from .stage_instance import StageInstance
from .threads import Thread
from .sticker import GuildSticker
from .file import File
from .audit_logs import AuditLogEntry
from .object import OLDEST_OBJECT, Object
from .profile import MemberProfile
from .partial_emoji import PartialEmoji
from .welcome_screen import *
from .application import PartialApplication
from .guild_premium import PremiumGuildSubscription
from .entitlements import Entitlement
from .automod import AutoModRule, AutoModTrigger, AutoModRuleAction
from .partial_emoji import _EmojiTag, PartialEmoji
from .commands import _command_factory

if TYPE_CHECKING:
    from .abc import Snowflake, SnowflakeTime
    from .types.guild import (
        BaseGuild as BaseGuildPayload,
        Guild as GuildPayload,
        RolePositionUpdate as RolePositionUpdatePayload,
        UserGuild as UserGuildPayload,
        IncidentData,
    )
    from .types.threads import (
        Thread as ThreadPayload,
    )
    from .types.voice import BaseVoiceState as VoiceStatePayload
    from .channel import VoiceChannel, StageChannel, TextChannel, ForumChannel, CategoryChannel
    from .template import Template
    from .webhook import Webhook
    from .state import ConnectionState
    from .voice_client import VoiceProtocol
    from .settings import GuildSettings
    from .enums import ApplicationType, EntitlementType
    from .types.channel import (
        GuildChannel as GuildChannelPayload,
        TextChannel as TextChannelPayload,
        NewsChannel as NewsChannelPayload,
        VoiceChannel as VoiceChannelPayload,
        CategoryChannel as CategoryChannelPayload,
        StageChannel as StageChannelPayload,
        ForumChannel as ForumChannelPayload,
        DirectoryChannel as DirectoryChannelPayload,
    )
    from .types.embed import EmbedType
    from .types.integration import IntegrationType
    from .types.message import MessageSearchAuthorType, MessageSearchHasType
    from .types.snowflake import SnowflakeList
    from .types.widget import EditWidgetSettings
    from .types.audit_log import AuditLogEvent
    from .types.oauth2 import OAuth2Guild as OAuth2GuildPayload
    from .message import EmojiInputType, Message
    from .read_state import ReadState
    from .commands import UserCommand, MessageCommand, SlashCommand

    VocalGuildChannel = Union[VoiceChannel, StageChannel]
    NonCategoryChannel = Union[VocalGuildChannel, ForumChannel, TextChannel, DirectoryChannel]
    GuildChannel = Union[NonCategoryChannel, CategoryChannel]
    ByCategoryItem = Tuple[Optional[CategoryChannel], List[NonCategoryChannel]]

MISSING = utils.MISSING

__all__ = (
    'Guild',
    'UserGuild',
    'BanEntry',
)


class BanEntry(NamedTuple):
    reason: Optional[str]
    user: User


class BulkBanResult(NamedTuple):
    banned: List[Object]
    failed: List[Object]


class DirectoryBroadcastEligibility(NamedTuple):
    can_broadcast: bool
    has_broadcast: bool


class _GuildLimit(NamedTuple):
    emoji: int
    stickers: int
    bitrate: float
    filesize: int


class UserGuild(Hashable):
    """Represents a partial joined guild.

    .. container:: operations

        .. describe:: x == y

            Checks if two guilds are equal.

        .. describe:: x != y

            Checks if two guilds are not equal.

        .. describe:: hash(x)

            Returns the guild's hash.

        .. describe:: str(x)

            Returns the guild's name.

    .. versionadded:: 2.0

    Attributes
    ----------
    id: :class:`int`
        The guild's ID.
    name: :class:`str`
        The guild name.
    features: List[:class:`str`]
        A list of features that the guild has. The features that a guild can have are
        subject to arbitrary change by Discord. Incomplete when retrieved from :attr:`OAuth2Authorization.guilds`.
    owner: :class:`bool`
        Whether the current user is the owner of the guild. Inaccurate when retrieved from :attr:`OAuth2Authorization.guilds`.
    mfa_level: :class:`MFALevel`
        The guild's Multi-Factor Authentication requirement level. Only available from :attr:`OAuth2Authorization.guilds`.

        .. versionadded:: 2.1
    approximate_member_count: Optional[:class:`int`]
        The approximate number of members in the guild. Only available using
        using :meth:`Client.fetch_guilds` with ``with_counts=True``.
    approximate_presence_count: Optional[:class:`int`]
        The approximate number of members currently active in the guild.
        Offline members are excluded. Only available using
        :meth:`Client.fetch_guilds` with ``with_counts=True``.
    """

    __slots__ = (
        'id',
        'name',
        '_icon',
        'owner',
        '_permissions',
        'mfa_level',
        'features',
        'approximate_member_count',
        'approximate_presence_count',
        '_state',
    )

    def __init__(self, *, state: ConnectionState, data: Union[UserGuildPayload, OAuth2GuildPayload]):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self.name: str = data['name']
        self._icon: Optional[str] = data.get('icon')
        self.owner: bool = data.get('owner', False)
        self._permissions: int = int(data.get('permissions', 0))
        self.mfa_level: MFALevel = try_enum(MFALevel, data.get('mfa_level', 0))
        self.features: List[str] = data.get('features', [])
        self.approximate_member_count: Optional[int] = data.get('approximate_member_count')
        self.approximate_presence_count: Optional[int] = data.get('approximate_presence_count')

    def __str__(self) -> str:
        return self.name or ''

    def __repr__(self) -> str:
        return f'<UserGuild id={self.id} name={self.name!r}>'

    @property
    def icon(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the guild's icon asset, if available."""
        if self._icon is None:
            return None
        return Asset._from_guild_icon(self._state, self.id, self._icon)

    @property
    def permissions(self) -> Permissions:
        """:class:`Permissions`: Returns the calculated permissions the current user has in the guild."""
        return Permissions(self._permissions)

    def is_joined(self) -> bool:
        """Returns whether you are a member of this guild.

        Always returns ``True``.

        Returns
        -------
        :class:`bool`
            Whether you are a member of this guild.
        """
        return True

    async def webhook_channels(self) -> List[PartialMessageable]:
        """|coro|

        Retrieves the channels that the current user can create webhooks in for the guild.

        .. versionadded:: 2.1

        Raises
        -------
        HTTPException
            Retrieving the webhook channels failed.

        Returns
        --------
        List[ :class:`PartialMessageable`]
            The channels that the current user can create webhooks in. Any :class:`PartialMessageable` will have its :attr:`PartialMessageable.name` filled in.
        """
        state = self._state
        data = await state.http.get_guild_webhook_channels(self.id)
        return [PartialMessageable._from_webhook_channel(self, c) for c in data]

    async def leave(self) -> None:
        """|coro|

        Leaves the guild.

        .. note::

            You cannot leave a guild that you own, you must delete it instead
            via :meth:`delete`.

        .. versionadded:: 2.1

        Raises
        --------
        HTTPException
            Leaving the guild failed.
        """
        await self._state.http.leave_guild(self.id, lurking=False)

    async def delete(self) -> None:
        """|coro|

        Deletes the guild. You must be the guild owner to delete the
        guild.

        .. versionadded:: 2.1

        Raises
        --------
        HTTPException
            Deleting the guild failed.
        Forbidden
            You do not have permissions to delete the guild.
        """
        await self._state.http.delete_guild(self.id)


class Guild(Hashable):
    """Represents a Discord guild.

    This is referred to as a "server" in the official Discord UI.

    .. container:: operations

        .. describe:: x == y

            Checks if two guilds are equal.

        .. describe:: x != y

            Checks if two guilds are not equal.

        .. describe:: hash(x)

            Returns the guild's hash.

        .. describe:: str(x)

            Returns the guild's name.

    .. versionchanged:: 2.1

        Removed ``application_command_counts`` and ``application_command_count`` as they are no longer provided by Discord.

    Attributes
    ----------
    name: :class:`str`
        The guild name.
    emojis: Tuple[:class:`Emoji`, ...]
        All emojis that the guild owns.
    stickers: Tuple[:class:`GuildSticker`, ...]
        All stickers that the guild owns.

        .. versionadded:: 2.0
    afk_timeout: :class:`int`
        The timeout to get sent to the AFK channel.
    id: :class:`int`
        The guild's ID.
    owner_id: :class:`int`
        The guild owner's ID.
    application_id: Optional[:class:`int`]
        The application ID of the guild owner (if applicable).

        .. versionadded:: 2.0

        .. versionchanged:: 2.1

            Renamed from ``owner_application_id`` to ``application_id``.
    unavailable: :class:`bool`
        Indicates if the guild is unavailable. If this is ``True`` then the
        reliability of other attributes outside of :attr:`Guild.id` is slim and they might
        all be ``None``. It is best to not do anything with the guild if it is unavailable.

        Check the :func:`on_guild_unavailable` and :func:`on_guild_available` events.
    max_presences: Optional[:class:`int`]
        The maximum amount of presences for the guild.
    max_members: Optional[:class:`int`]
        The maximum amount of members for the guild.
    max_video_channel_users: Optional[:class:`int`]
        The maximum amount of users in a video stream.

        .. versionadded:: 1.4
    max_stage_video_channel_users: Optional[:class:`int`]
        The maximum amount of users in a stage video stream.

        .. versionadded:: 2.1
    description: Optional[:class:`str`]
        The guild's description.
    verification_level: :class:`VerificationLevel`
        The guild's verification level.
    vanity_url_code: Optional[:class:`str`]
        The guild's vanity url code, if any

        .. versionadded:: 2.0
    explicit_content_filter: :class:`ContentFilter`
        The guild's explicit content filter.
    default_notifications: :class:`NotificationLevel`
        The guild's notification settings.
    features: List[:class:`str`]
        A list of features that the guild has. The features that a guild can have are
        subject to arbitrary change by Discord.
    premium_subscription_count: :class:`int`
        The number of "boosts" this guild currently has.
    preferred_locale: :class:`Locale`
        The preferred locale for the guild. Used when filtering Server Discovery
        results to a specific language.

        .. versionchanged:: 2.0
            This field is now an enum instead of a :class:`str`.
    nsfw_level: :class:`NSFWLevel`
        The guild's NSFW level.

        .. versionadded:: 2.0
    mfa_level: :class:`MFALevel`
        The guild's Multi-Factor Authentication requirement level.

        .. versionchanged:: 2.0
            This field is now an enum instead of an :class:`int`.
    approximate_member_count: Optional[:class:`int`]
        The approximate number of members in the guild. This is ``None`` unless the guild is obtained
        using :meth:`Client.fetch_guild` with ``with_counts=True``.

        .. versionadded:: 2.0
    approximate_presence_count: Optional[:class:`int`]
        The approximate number of members currently active in the guild.
        Offline members are excluded. This is ``None`` unless the guild is obtained using
        :meth:`Client.fetch_guild` with ``with_counts=True``.

        .. versionadded:: 2.0
    premium_progress_bar_enabled: :class:`bool`
        Indicates if the guild has the premium (server boost) progress bar enabled.

        .. versionadded:: 2.0
    widget_enabled: :class:`bool`
        Indicates if the guild has widget enabled.

        .. versionadded:: 2.0
    hub_type: Optional[:class:`HubType`]
        The type of Student Hub the guild is, if applicable.

        .. versionadded:: 2.1
    """

    __slots__ = (
        'afk_timeout',
        'name',
        'id',
        'unavailable',
        'owner_id',
        'emojis',
        'stickers',
        'features',
        'verification_level',
        'explicit_content_filter',
        'default_notifications',
        'description',
        'max_presences',
        'max_members',
        'max_video_channel_users',
        'max_stage_video_channel_users',
        '_premium_tier',
        'premium_subscription_count',
        'preferred_locale',
        'nsfw_level',
        'mfa_level',
        'vanity_url_code',
        'application_id',
        'widget_enabled',
        '_widget_channel_id',
        '_members',
        '_channels',
        '_icon',
        '_banner',
        '_state',
        '_roles',
        '_member_count',
        '_large',
        '_splash',
        '_voice_states',
        '_afk_channel_id',
        '_system_channel_id',
        '_system_channel_flags',
        '_discovery_splash',
        '_rules_channel_id',
        '_public_updates_channel_id',
        '_safety_alerts_channel_id',
        '_stage_instances',
        '_scheduled_events',
        '_threads',
        'approximate_member_count',
        'approximate_presence_count',
        'premium_progress_bar_enabled',
        '_presence_count',
        '_true_online_count',
        '_member_list',
        'keywords',
        'primary_category_id',
        'hub_type',
        '_joined_at',
        '_cs_joined',
        '_incidents_data',
    )

    _PREMIUM_GUILD_LIMITS: ClassVar[Dict[int, _GuildLimit]] = {
        0: _GuildLimit(emoji=50, stickers=5, bitrate=96e3, filesize=utils.DEFAULT_FILE_SIZE_LIMIT_BYTES),
        1: _GuildLimit(emoji=100, stickers=15, bitrate=128e3, filesize=utils.DEFAULT_FILE_SIZE_LIMIT_BYTES),
        2: _GuildLimit(emoji=150, stickers=30, bitrate=256e3, filesize=52428800),
        3: _GuildLimit(emoji=250, stickers=60, bitrate=384e3, filesize=104857600),
    }

    def __init__(self, *, data: Union[BaseGuildPayload, GuildPayload], state: ConnectionState) -> None:
        self._cs_joined: Optional[bool] = None
        self._roles: Dict[int, Role] = {}
        self._channels: Dict[int, GuildChannel] = {}
        self._members: Dict[int, Member] = {}
        self._member_list: List[Optional[Member]] = []
        self._voice_states: Dict[int, VoiceState] = {}
        self._threads: Dict[int, Thread] = {}
        self._stage_instances: Dict[int, StageInstance] = {}
        self._scheduled_events: Dict[int, ScheduledEvent] = {}
        self._state: ConnectionState = state
        self._member_count: Optional[int] = None
        self._presence_count: Optional[int] = None
        self._large: Optional[bool] = None
        self._from_data(data)

    def _add_channel(self, channel: GuildChannel, /) -> None:
        self._channels[channel.id] = channel

    def _remove_channel(self, channel: Snowflake, /) -> None:
        self._channels.pop(channel.id, None)

    def _voice_state_for(self, user_id: int, /) -> Optional[VoiceState]:
        return self._voice_states.get(user_id)

    def _add_member(self, member: Member, /) -> None:
        self._members[member.id] = member
        if member._presence:
            self._state.store_presence(member.id, member._presence, self.id)
            member._presence = None

    def _store_thread(self, payload: ThreadPayload, /) -> Thread:
        thread = Thread(guild=self, state=self._state, data=payload)
        self._threads[thread.id] = thread
        return thread

    def _remove_member(self, member: Snowflake, /) -> None:
        self._members.pop(member.id, None)
        self._state.remove_presence(member.id, self.id)

    def _add_thread(self, thread: Thread, /) -> None:
        self._threads[thread.id] = thread

    def _remove_thread(self, thread: Snowflake, /) -> None:
        self._threads.pop(thread.id, None)

    def _remove_threads_by_channel(self, channel_id: int) -> List[Thread]:
        to_remove = [t for t in self._threads.values() if t.parent_id == channel_id]
        for thread in to_remove:
            del self._threads[thread.id]
        return to_remove

    def _filter_threads(self, channel_ids: Set[int]) -> Dict[int, Thread]:
        return {k: t for k, t in self._threads.items() if t.parent_id in channel_ids}

    def __str__(self) -> str:
        return self.name or ''

    def __repr__(self) -> str:
        attrs = (
            ('id', self.id),
            ('name', self.name),
            ('chunked', self.chunked),
            ('member_count', self.member_count),
        )
        inner = ' '.join('%s=%r' % t for t in attrs)
        return f'<Guild {inner}>'

    def _update_voice_state(
        self, data: VoiceStatePayload, channel_id: Optional[int]
    ) -> Tuple[Optional[Member], VoiceState, VoiceState]:
        cache_flags = self._state.member_cache_flags
        user_id = int(data['user_id'])
        channel: Optional[VocalGuildChannel] = self.get_channel(channel_id)  # type: ignore # this will always be a voice channel
        try:
            # Check if we should remove the voice state from cache
            if channel is None:
                after = self._voice_states.pop(user_id)
            else:
                after = self._voice_states[user_id]

            before = copy.copy(after)
            after._update(data, channel)
        except KeyError:
            # If we're here then add it into the cache
            after = VoiceState(data=data, channel=channel)
            before = VoiceState(data=data, channel=None)
            self._voice_states[user_id] = after

        member = self.get_member(user_id)
        if member is None:
            try:
                member_data = data['member']  # pyright: ignore[reportTypedDictNotRequiredAccess]
                member = Member(data=member_data, state=self._state, guild=self)
            except KeyError:
                member = None

            if member is not None and cache_flags.voice:
                self._add_member(member)

        return member, before, after

    def _add_role(self, role: Role, /) -> None:
        self._roles[role.id] = role

    def _remove_role(self, role_id: int, /) -> Role:
        # This raises KeyError if it fails..
        return self._roles.pop(role_id)

    @classmethod
    def _create_unavailable(cls, *, state: ConnectionState, guild_id: int) -> Guild:
        return cls(state=state, data={'id': guild_id, 'unavailable': True})  # type: ignore

    def _from_data(self, guild: Union[BaseGuildPayload, GuildPayload]) -> None:
        try:
            self._member_count: Optional[int] = guild['member_count']  # type: ignore # Handled below
        except KeyError:
            pass

        self.id: int = int(guild['id'])
        self.name: str = guild.get('name', '')
        self.verification_level: VerificationLevel = try_enum(VerificationLevel, guild.get('verification_level'))
        self.default_notifications: NotificationLevel = try_enum(
            NotificationLevel, guild.get('default_message_notifications')
        )
        self.explicit_content_filter: ContentFilter = try_enum(ContentFilter, guild.get('explicit_content_filter', 0))
        self.afk_timeout: int = guild.get('afk_timeout', 0)
        self.hub_type: Optional[HubType] = (
            try_enum(HubType, guild.get('hub_type')) if guild.get('hub_type') is not None else None
        )
        self.unavailable: bool = guild.get('unavailable', False)
        if self.unavailable:
            self._member_count = 0

        state = self._state  # Speed up attribute access

        for r in guild.get('roles', []):
            role = Role(guild=self, data=r, state=state)
            self._roles[role.id] = role

        for c in guild.get('channels', []):
            factory, _ = _guild_channel_factory(c['type'])
            if factory:
                self._add_channel(factory(guild=self, data=c, state=state))  # type: ignore

        for t in guild.get('threads', []):
            self._add_thread(Thread(guild=self, state=self._state, data=t))

        for s in guild.get('stage_instances', []):
            stage_instance = StageInstance(guild=self, data=s, state=state)
            self._stage_instances[stage_instance.id] = stage_instance

        for s in guild.get('guild_scheduled_events', []):
            scheduled_event = ScheduledEvent(data=s, state=state)
            self._scheduled_events[scheduled_event.id] = scheduled_event

        self.emojis: Tuple[Emoji, ...] = tuple(map(lambda d: state.store_emoji(self, d), guild.get('emojis', [])))
        self.stickers: Tuple[GuildSticker, ...] = tuple(
            map(lambda d: state.store_sticker(self, d), guild.get('stickers', []))
        )
        self.features: List[str] = guild.get('features', [])
        self._icon: Optional[str] = guild.get('icon')
        self._banner: Optional[str] = guild.get('banner')
        self._splash: Optional[str] = guild.get('splash')
        self._system_channel_id: Optional[int] = utils._get_as_snowflake(guild, 'system_channel_id')
        self.description: Optional[str] = guild.get('description')
        self.max_presences: Optional[int] = guild.get('max_presences')
        self.max_members: Optional[int] = guild.get('max_members')
        self.max_video_channel_users: Optional[int] = guild.get('max_video_channel_users')
        self.max_stage_video_channel_users: Optional[int] = guild.get('max_stage_video_channel_users')
        self._premium_tier = guild.get('premium_tier')
        self.premium_subscription_count: int = guild.get('premium_subscription_count') or 0
        self.vanity_url_code: Optional[str] = guild.get('vanity_url_code')
        self.widget_enabled: bool = guild.get('widget_enabled', False)
        self._widget_channel_id: Optional[int] = utils._get_as_snowflake(guild, 'widget_channel_id')
        self._system_channel_flags: int = guild.get('system_channel_flags', 0)
        self.preferred_locale: Locale = try_enum(Locale, guild.get('preferred_locale', 'en-US'))
        self._discovery_splash: Optional[str] = guild.get('discovery_splash')
        self._rules_channel_id: Optional[int] = utils._get_as_snowflake(guild, 'rules_channel_id')
        self._public_updates_channel_id: Optional[int] = utils._get_as_snowflake(guild, 'public_updates_channel_id')
        self._safety_alerts_channel_id: Optional[int] = utils._get_as_snowflake(guild, 'safety_alerts_channel_id')
        self._afk_channel_id: Optional[int] = utils._get_as_snowflake(guild, 'afk_channel_id')
        self.nsfw_level: NSFWLevel = try_enum(NSFWLevel, guild.get('nsfw_level', 0))
        self.mfa_level: MFALevel = try_enum(MFALevel, guild.get('mfa_level', 0))
        self.approximate_presence_count: Optional[int] = guild.get('approximate_presence_count')
        self.approximate_member_count: Optional[int] = guild.get('approximate_member_count')
        self.owner_id: Optional[int] = utils._get_as_snowflake(guild, 'owner_id')
        self.application_id: Optional[int] = utils._get_as_snowflake(guild, 'application_id')
        self.premium_progress_bar_enabled: bool = guild.get('premium_progress_bar_enabled', False)
        self._joined_at = guild.get('joined_at')
        self._incidents_data: Optional[IncidentData] = guild.get('incidents_data')

        try:
            self._large = guild['large']  # type: ignore
        except KeyError:
            pass

        for vs in guild.get('voice_states', []):
            self._update_voice_state(vs, int(vs['channel_id']))

        cache_flags = state.member_cache_flags
        for mdata in guild.get('members', []):
            member = Member(data=mdata, guild=self, state=state)
            if cache_flags.joined or member.id == state.self_id or (cache_flags.voice and member.id in self._voice_states):
                self._add_member(member)

        for presence in guild.get('presences', []):
            user_id = int(presence['user']['id'])
            presence = state.create_presence(presence)
            state.store_presence(user_id, presence, self.id)

    @property
    def channels(self) -> Sequence[GuildChannel]:
        """Sequence[:class:`abc.GuildChannel`]: A list of channels that belongs to this guild."""
        return utils.SequenceProxy(self._channels.values())

    @property
    def threads(self) -> Sequence[Thread]:
        """Sequence[:class:`Thread`]: A list of active threads that you have permission to view.

        .. versionadded:: 2.0
        """
        return utils.SequenceProxy(self._threads.values())

    @property
    def large(self) -> bool:
        """:class:`bool`: Indicates if the guild is a 'large' guild.

        A large guild is defined as having more than ``large_threshold`` count
        members, which for this library is set to the maximum of 250.
        """
        if self._large is None:
            if self._member_count is not None:
                return self._member_count >= 250
            return len(self._members) >= 250
        return self._large

    @property
    def _offline_members_hidden(self) -> bool:
        # Member count, hoisted role count, and Online/Offline group
        # This may not be 100% accurate because member list groups are cached server-side
        return (self._member_count or 0) + len([role for role in self.roles if role.hoist]) + 2 >= 1000

    @property
    def _extra_large(self) -> bool:
        return self._member_count is not None and self._member_count >= 75000

    @property
    def max_stage_video_users(self) -> Optional[int]:
        """Optional[:class:`int`]: The maximum amount of users in a stage video stream.

        An alias for :attr:`max_stage_video_channel_users`.

        .. versionadded:: 2.1
        """
        return self.max_stage_video_channel_users

    def is_hub(self) -> bool:
        """:class:`bool`: Whether the guild is a Student Hub.

        .. versionadded:: 2.1
        """
        return 'HUB' in self.features

    @property
    def voice_channels(self) -> List[VoiceChannel]:
        """List[:class:`VoiceChannel`]: A list of voice channels that belongs to this guild.

        This is sorted by the position and are in UI order from top to bottom.
        """
        r = [ch for ch in self._channels.values() if isinstance(ch, VoiceChannel)]
        r.sort(key=attrgetter('position', 'id'))
        return r

    @property
    def stage_channels(self) -> List[StageChannel]:
        """List[:class:`StageChannel`]: A list of stage channels that belongs to this guild.

        .. versionadded:: 1.7

        This is sorted by the position and are in UI order from top to bottom.
        """
        r = [ch for ch in self._channels.values() if isinstance(ch, StageChannel)]
        r.sort(key=attrgetter('position', 'id'))
        return r

    @property
    def me(self) -> Optional[Member]:
        """Optional[:class:`Member`]: Similar to :attr:`Client.user` except an instance of :class:`Member`.
        This is essentially used to get the member version of yourself.

        .. versionchanged:: 2.0

            The type has been updated to be optional, which properly reflects cases where the current user
            is not a member of the guild, or the current user's member object is not cached.
        """
        self_id = self._state.self_id
        return self.get_member(self_id)  # type: ignore

    def is_joined(self) -> bool:
        """Returns whether you are a full member of this guild.

        May not be accurate for :class:`Guild` s fetched over HTTP.

        .. versionadded:: 2.0

        Returns
        -------
        :class:`bool`
            Whether you are a member of this guild.
        """
        if self._cs_joined is not None:
            return self._cs_joined
        if (self.me and self.me.joined_at) or self.joined_at:
            return True
        return self._state.is_guild_evicted(self)

    @property
    def joined_at(self) -> Optional[datetime]:
        """:class:`datetime.datetime`: Returns when you joined the guild.

        .. versionadded:: 2.0
        """
        return utils.parse_time(self._joined_at)

    @property
    def voice_client(self) -> Optional[VoiceProtocol]:
        """Optional[:class:`VoiceProtocol`]: Returns the :class:`VoiceProtocol` associated with this guild, if any."""
        return self._state._get_voice_client(self.id)

    @property
    def notification_settings(self) -> GuildSettings:
        """:class:`GuildSettings`: Returns the notification settings for the guild.

        If not found, an instance is created with defaults applied. This follows Discord behaviour.

        .. versionadded:: 2.0
        """
        state = self._state
        return state.guild_settings.get(self.id, state.default_guild_settings(self.id))

    @property
    def text_channels(self) -> List[TextChannel]:
        """List[:class:`TextChannel`]: A list of text channels that belongs to this guild.

        This is sorted by the position and are in UI order from top to bottom.
        """
        r = [ch for ch in self._channels.values() if isinstance(ch, TextChannel)]
        r.sort(key=attrgetter('position', 'id'))
        return r

    @property
    def categories(self) -> List[CategoryChannel]:
        """List[:class:`CategoryChannel`]: A list of categories that belongs to this guild.

        This is sorted by the position and are in UI order from top to bottom.
        """
        r = [ch for ch in self._channels.values() if isinstance(ch, CategoryChannel)]
        r.sort(key=attrgetter('position', 'id'))
        return r

    @property
    def forums(self) -> List[ForumChannel]:
        """List[:class:`ForumChannel`]: A list of forum channels that belongs to this guild.

        This is sorted by the position and are in UI order from top to bottom.

        .. versionadded:: 2.0
        """
        r = [ch for ch in self._channels.values() if isinstance(ch, ForumChannel)]
        r.sort(key=attrgetter('position', 'id'))
        return r

    @property
    def directory_channels(self) -> List[DirectoryChannel]:
        """List[:class:`DirectoryChannel`]: A list of directory channels that belongs to this guild.

        This is sorted by the position and are in UI order from top to bottom.

        .. versionadded:: 2.1
        """
        r = [ch for ch in self._channels.values() if isinstance(ch, DirectoryChannel)]
        r.sort(key=attrgetter('position', 'id'))
        return r

    @property
    def directories(self) -> List[DirectoryChannel]:
        """List[:class:`DirectoryChannel`]: A list of directory channels that belongs to this guild.

        An alias for :attr:`Guild.directory_channels`.

        .. versionadded:: 2.1
        """
        return self.directory_channels

    def by_category(self) -> List[ByCategoryItem]:
        """Returns every :class:`CategoryChannel` and their associated channels.

        These channels and categories are sorted in the official Discord UI order.

        If the channels do not have a category, then the first element of the tuple is
        ``None``.

        Returns
        --------
        List[Tuple[Optional[:class:`CategoryChannel`], List[:class:`abc.GuildChannel`]]]:
            The categories and their associated channels.
        """
        grouped: Dict[Optional[int], List[NonCategoryChannel]] = {}
        for channel in self._channels.values():
            if isinstance(channel, CategoryChannel):
                grouped.setdefault(channel.id, [])
                continue

            try:
                grouped[channel.category_id].append(channel)
            except KeyError:
                grouped[channel.category_id] = [channel]

        def key(t: ByCategoryItem) -> Tuple[Tuple[int, int], List[NonCategoryChannel]]:
            k, v = t
            return ((k.position, k.id) if k else (-1, -1), v)

        _get = self._channels.get
        as_list: List[ByCategoryItem] = [(_get(k), v) for k, v in grouped.items()]  # type: ignore
        as_list.sort(key=key)
        for _, channels in as_list:
            channels.sort(key=attrgetter('_sorting_bucket', 'position', 'id'))
        return as_list

    def _resolve_channel(self, id: Optional[int], /) -> Optional[Union[GuildChannel, Thread]]:
        if id is None:
            return

        return self._channels.get(id) or self._threads.get(id)

    def get_channel_or_thread(self, channel_id: int, /) -> Optional[Union[Thread, GuildChannel]]:
        """Returns a channel or thread with the given ID.

        .. versionadded:: 2.0

        Parameters
        -----------
        channel_id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[Union[:class:`Thread`, :class:`.abc.GuildChannel`]]
            The returned channel, thread, or ``None`` if not found.
        """
        return self._channels.get(channel_id) or self._threads.get(channel_id)

    def get_channel(self, channel_id: int, /) -> Optional[GuildChannel]:
        """Returns a channel with the given ID.

        .. note::

            This does *not* search for threads.

        .. versionchanged:: 2.0

            ``channel_id`` parameter is now positional-only.

        Parameters
        -----------
        channel_id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`.abc.GuildChannel`]
            The returned channel or ``None`` if not found.
        """
        return self._channels.get(channel_id)

    def get_thread(self, thread_id: int, /) -> Optional[Thread]:
        """Returns a thread with the given ID.

        .. note::

            This does not always retrieve archived threads, as they are not retained in the internal
            cache. Use :func:`fetch_channel` instead.

        .. versionadded:: 2.0

        Parameters
        -----------
        thread_id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`Thread`]
            The returned thread or ``None`` if not found.
        """
        return self._threads.get(thread_id)

    def get_emoji(self, emoji_id: int, /) -> Optional[Emoji]:
        """Returns an emoji with the given ID.

        .. versionadded:: 2.0

        Parameters
        ----------
        emoji_id: int
            The ID to search for.

        Returns
        --------
        Optional[:class:`Emoji`]
            The returned Emoji or ``None`` if not found.
        """
        emoji = self._state.get_emoji(emoji_id)
        if emoji and emoji.guild == self:
            return emoji
        return None

    @property
    def system_channel(self) -> Optional[TextChannel]:
        """Optional[:class:`TextChannel`]: Returns the guild's channel used for system messages.

        If no channel is set, then this returns ``None``.
        """
        channel_id = self._system_channel_id
        return channel_id and self._channels.get(channel_id)  # type: ignore

    @property
    def system_channel_flags(self) -> SystemChannelFlags:
        """:class:`SystemChannelFlags`: Returns the guild's system channel settings."""
        return SystemChannelFlags._from_value(self._system_channel_flags)

    @property
    def rules_channel(self) -> Optional[TextChannel]:
        """Optional[:class:`TextChannel`]: Return's the guild's channel used for the rules.
        The guild must be a Community guild.

        If no channel is set, then this returns ``None``.

        .. versionadded:: 1.3
        """
        channel_id = self._rules_channel_id
        return channel_id and self._channels.get(channel_id)  # type: ignore

    @property
    def public_updates_channel(self) -> Optional[TextChannel]:
        """Optional[:class:`TextChannel`]: Return's the guild's channel where admins and
        moderators of the guilds receive notices from Discord. The guild must be a
        Community guild.

        If no channel is set, then this returns ``None``.

        .. versionadded:: 1.4
        """
        channel_id = self._public_updates_channel_id
        return channel_id and self._channels.get(channel_id)  # type: ignore

    @property
    def safety_alerts_channel(self) -> Optional[TextChannel]:
        """Optional[:class:`TextChannel`]: Return's the guild's channel used for safety alerts, if set.

        For example, this is used for the raid protection setting. The guild must have the ``COMMUNITY`` feature.

        .. versionadded:: 2.1
        """
        channel_id = self._safety_alerts_channel_id
        return channel_id and self._channels.get(channel_id)  # type: ignore

    @property
    def afk_channel(self) -> Optional[VocalGuildChannel]:
        """Optional[:class:`VoiceChannel`]: Returns the guild channel AFK users are moved to.

        If no channel is set, then this returns ``None``.
        """
        channel_id = self._afk_channel_id
        return channel_id and self._channels.get(channel_id)  # type: ignore

    @property
    def widget_channel(self) -> Optional[Union[TextChannel, ForumChannel, VoiceChannel, StageChannel]]:
        """Optional[Union[:class:`TextChannel`, :class:`ForumChannel`, :class:`VoiceChannel`, :class:`StageChannel`]]: Returns
        the widget channel of the guild.

        If no channel is set, then this returns ``None``.

        .. versionadded:: 2.0
        """
        channel_id = self._widget_channel_id
        return channel_id and self._channels.get(channel_id)  # type: ignore

    @property
    def emoji_limit(self) -> int:
        """:class:`int`: The maximum number of emoji slots this guild has."""
        more_emoji = 200 if 'MORE_EMOJI' in self.features else 50
        return max(more_emoji, self._PREMIUM_GUILD_LIMITS[self.premium_tier].emoji)

    @property
    def sticker_limit(self) -> int:
        """:class:`int`: The maximum number of sticker slots this guild has.

        .. versionadded:: 2.0
        """
        more_stickers = 60 if 'MORE_STICKERS' in self.features else 0
        return max(more_stickers, self._PREMIUM_GUILD_LIMITS[self.premium_tier].stickers)

    @property
    def bitrate_limit(self) -> float:
        """:class:`float`: The maximum bitrate for voice channels this guild can have."""
        vip_guild = self._PREMIUM_GUILD_LIMITS[1].bitrate if 'VIP_REGIONS' in self.features else 96e3
        return max(vip_guild, self._PREMIUM_GUILD_LIMITS[self.premium_tier].bitrate)

    @property
    def filesize_limit(self) -> int:
        """:class:`int`: The maximum number of bytes files can have when uploaded to this guild."""
        return self._PREMIUM_GUILD_LIMITS[self.premium_tier].filesize

    @property
    def members(self) -> Sequence[Member]:
        """Sequence[:class:`Member`]: A list of members that belong to this guild."""
        return utils.SequenceProxy(self._members.values())

    def get_member(self, user_id: int, /) -> Optional[Member]:
        """Returns a member with the given ID.

        .. versionchanged:: 2.0

            ``user_id`` parameter is now positional-only.

        Parameters
        -----------
        user_id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`Member`]
            The member or ``None`` if not found.
        """
        return self._members.get(user_id)

    @property
    def premium_tier(self) -> int:
        """:class:`int`: The premium tier for this guild. Corresponds to "Server Boost Level" in the official UI.
        The number goes from 0 to 3 inclusive.
        """
        tier = self._premium_tier
        if tier is not None:
            return tier
        if 'PREMIUM_TIER_3_OVERRIDE' in self.features:
            return 3

        # Fallback to calculating by the number of boosts
        count = self.premium_subscription_count
        if count < 2:
            return 0
        elif count < 7:
            return 1
        elif count < 14:
            return 2
        else:
            return 3

    @property
    def premium_subscribers(self) -> List[Member]:
        """List[:class:`Member`]: A list of members who have subscribed to (boosted) this guild."""
        return [member for member in self.members if member.premium_since is not None]

    @property
    def roles(self) -> Sequence[Role]:
        """Sequence[:class:`Role`]: Returns a sequence of the guild's roles in hierarchy order.

        The first element of this sequence will be the lowest role in the
        hierarchy.
        """
        return utils.SequenceProxy(self._roles.values(), sorted=True)

    def get_role(self, role_id: int, /) -> Optional[Role]:
        """Returns a role with the given ID.

        .. versionchanged:: 2.0

            ``role_id`` parameter is now positional-only.

        Parameters
        -----------
        role_id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`Role`]
            The role or ``None`` if not found.
        """
        return self._roles.get(role_id)

    @property
    def default_role(self) -> Role:
        """:class:`Role`: Gets the @everyone role that all members have by default."""
        # The @everyone role is *always* given
        return self.get_role(self.id)  # type: ignore

    @property
    def premium_subscriber_role(self) -> Optional[Role]:
        """Optional[:class:`Role`]: Gets the premium subscriber role, AKA "boost" role, in this guild.

        .. versionadded:: 1.6
        """
        for role in self._roles.values():
            if role.is_premium_subscriber():
                return role
        return None

    @property
    def stage_instances(self) -> Sequence[StageInstance]:
        """Sequence[:class:`StageInstance`]: Returns a sequence of the guild's stage instances that
        are currently running.

        .. versionadded:: 2.0
        """
        return utils.SequenceProxy(self._stage_instances.values())

    def get_stage_instance(self, stage_instance_id: int, /) -> Optional[StageInstance]:
        """Returns a stage instance with the given ID.

        .. versionadded:: 2.0

        Parameters
        -----------
        stage_instance_id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`StageInstance`]
            The stage instance or ``None`` if not found.
        """
        return self._stage_instances.get(stage_instance_id)

    @property
    def scheduled_events(self) -> Sequence[ScheduledEvent]:
        """Sequence[:class:`ScheduledEvent`]: Returns a sequence of the guild's scheduled events.

        .. versionadded:: 2.0
        """
        return utils.SequenceProxy(self._scheduled_events.values())

    @property
    def scheduled_events_read_state(self) -> ReadState:
        """:class:`ReadState`: Returns the read state representing the guild's scheduled events.

        .. versionadded:: 2.1
        """
        return self._state.get_read_state(self.id, ReadStateType.scheduled_events)

    @property
    def acked_scheduled_event(self) -> Optional[ScheduledEvent]:
        """Optional[:class:`ScheduledEvent`]: Returns the last scheduled event that the user has acknowledged.

        .. versionadded:: 2.1
        """
        return self._scheduled_events.get(self.scheduled_events_read_state.last_acked_id)

    def get_scheduled_event(self, scheduled_event_id: int, /) -> Optional[ScheduledEvent]:
        """Returns a scheduled event with the given ID.

        .. versionadded:: 2.0

        Parameters
        -----------
        scheduled_event_id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`ScheduledEvent`]
            The scheduled event or ``None`` if not found.
        """
        return self._scheduled_events.get(scheduled_event_id)

    @property
    def owner(self) -> Optional[Member]:
        """Optional[:class:`Member`]: The member that owns the guild."""
        return self.get_member(self.owner_id)  # type: ignore

    @property
    def icon(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the guild's icon asset, if available."""
        if self._icon is None:
            return None
        return Asset._from_guild_icon(self._state, self.id, self._icon)

    @property
    def banner(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the guild's banner asset, if available."""
        if self._banner is None:
            return None
        return Asset._from_guild_image(self._state, self.id, self._banner, path='banners')

    @property
    def splash(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the guild's invite splash asset, if available."""
        if self._splash is None:
            return None
        return Asset._from_guild_image(self._state, self.id, self._splash, path='splashes')

    @property
    def discovery_splash(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the guild's discovery splash asset, if available."""
        if self._discovery_splash is None:
            return None
        return Asset._from_guild_image(self._state, self.id, self._discovery_splash, path='discovery-splashes')

    @property
    def member_count(self) -> Optional[int]:
        """Optional[:class:`int`]: Returns the member count if available.

        .. warning::

            Due to a Discord limitation, this may not always be up-to-date and accurate.
        """
        return self._member_count if self._member_count is not None else self.approximate_member_count

    @property
    def online_count(self) -> Optional[int]:
        """Optional[:class:`int`]: Returns the online member count.

        .. versionadded:: 1.9

        .. warning::

            Due to a Discord limitation, this may not always be up-to-date and accurate.
        """
        return self._presence_count

    @property
    def chunked(self) -> bool:
        """:class:`bool`: Returns a boolean indicating if the guild is "chunked".

        A chunked guild means that the guild member count is equal to the
        number of members stored in the internal :attr:`members` cache.

        If this value returns ``False``, then you should request for
        offline members.
        """
        count = self._member_count
        if count is None:
            return False

        # Member updates must be enabled to have an accurate member count
        return count == len(self._members) and self._state.subscriptions.has_feature(self, 'member_updates')

    @property
    def created_at(self) -> datetime:
        """:class:`datetime.datetime`: Returns the guild's creation time in UTC."""
        return utils.snowflake_time(self.id)

    def get_member_named(self, name: str, /) -> Optional[Member]:
        """Returns the first member found that matches the name provided.

        The name is looked up in the following order:

        - Username#Discriminator (deprecated)
        - Username#0 (deprecated, only gets users that migrated from their discriminator)
        - Nickname
        - Global name
        - Username

        If no member is found, ``None`` is returned.

        .. versionchanged:: 2.0

            ``name`` parameter is now positional-only.

        .. deprecated:: 2.1

            Looking up users via discriminator due to Discord API change.

        Parameters
        -----------
        name: :class:`str`
            The name of the member to lookup.

        Returns
        --------
        Optional[:class:`Member`]
            The member in this guild with the associated name. If not found
            then ``None`` is returned.
        """

        members = self.members

        username, _, discriminator = name.rpartition('#')

        # If # isn't found then "discriminator" actually has the username
        if not username:
            discriminator, username = username, discriminator

        if discriminator == '0' or (len(discriminator) == 4 and discriminator.isdigit()):
            return utils.find(lambda m: m.name == username and m.discriminator == discriminator, members)

        def pred(m: Member) -> bool:
            return m.nick == name or m.global_name == name or m.name == name

        return utils.find(pred, members)

    @overload
    def _create_channel(
        self,
        name: str,
        channel_type: Literal[ChannelType.text],
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = ...,
        category: Optional[Snowflake] = ...,
        **options: Any,
    ) -> Coroutine[Any, Any, TextChannelPayload]:
        ...

    @overload
    def _create_channel(
        self,
        name: str,
        channel_type: Literal[ChannelType.voice],
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = ...,
        category: Optional[Snowflake] = ...,
        **options: Any,
    ) -> Coroutine[Any, Any, VoiceChannelPayload]:
        ...

    @overload
    def _create_channel(
        self,
        name: str,
        channel_type: Literal[ChannelType.stage_voice],
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = ...,
        category: Optional[Snowflake] = ...,
        **options: Any,
    ) -> Coroutine[Any, Any, StageChannelPayload]:
        ...

    @overload
    def _create_channel(
        self,
        name: str,
        channel_type: Literal[ChannelType.category],
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = ...,
        category: Optional[Snowflake] = ...,
        **options: Any,
    ) -> Coroutine[Any, Any, CategoryChannelPayload]:
        ...

    @overload
    def _create_channel(
        self,
        name: str,
        channel_type: Literal[ChannelType.news],
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = ...,
        category: Optional[Snowflake] = ...,
        **options: Any,
    ) -> Coroutine[Any, Any, NewsChannelPayload]:
        ...

    @overload
    def _create_channel(
        self,
        name: str,
        channel_type: Literal[ChannelType.news, ChannelType.text],
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = ...,
        category: Optional[Snowflake] = ...,
        **options: Any,
    ) -> Coroutine[Any, Any, Union[TextChannelPayload, NewsChannelPayload]]:
        ...

    @overload
    def _create_channel(
        self,
        name: str,
        channel_type: Literal[ChannelType.forum],
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = ...,
        category: Optional[Snowflake] = ...,
        **options: Any,
    ) -> Coroutine[Any, Any, ForumChannelPayload]:
        ...

    @overload
    def _create_channel(
        self,
        name: str,
        channel_type: Literal[ChannelType.directory],
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = ...,
        category: Optional[Snowflake] = ...,
        **options: Any,
    ) -> Coroutine[Any, Any, DirectoryChannelPayload]:
        ...

    @overload
    def _create_channel(
        self,
        name: str,
        channel_type: ChannelType,
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = ...,
        category: Optional[Snowflake] = ...,
        **options: Any,
    ) -> Coroutine[Any, Any, GuildChannelPayload]:
        ...

    def _create_channel(
        self,
        name: str,
        channel_type: ChannelType,
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = MISSING,
        category: Optional[Snowflake] = None,
        **options: Any,
    ) -> Coroutine[Any, Any, GuildChannelPayload]:
        if overwrites is MISSING:
            overwrites = {}
        elif not isinstance(overwrites, Mapping):
            raise TypeError('overwrites parameter expects a dict')

        perms = []
        for target, perm in overwrites.items():
            if not isinstance(perm, PermissionOverwrite):
                raise TypeError(f'Expected PermissionOverwrite received {perm.__class__.__name__}')

            allow, deny = perm.pair()
            payload = {'allow': allow.value, 'deny': deny.value, 'id': target.id}

            if isinstance(target, Role):
                payload['type'] = abc._Overwrites.ROLE
            else:
                payload['type'] = abc._Overwrites.MEMBER

            perms.append(payload)

        parent_id = category.id if category else None
        return self._state.http.create_channel(
            self.id, channel_type.value, name=name, parent_id=parent_id, permission_overwrites=perms, **options
        )

    async def create_text_channel(
        self,
        name: str,
        *,
        reason: Optional[str] = None,
        category: Optional[CategoryChannel] = None,
        news: bool = False,
        position: int = MISSING,
        topic: str = MISSING,
        slowmode_delay: int = MISSING,
        nsfw: bool = MISSING,
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = MISSING,
        default_auto_archive_duration: int = MISSING,
        default_thread_slowmode_delay: int = MISSING,
    ) -> TextChannel:
        """|coro|

        Creates a :class:`TextChannel` for the guild.

        Note that you must have :attr:`~Permissions.manage_channels` to create the channel.

        The ``overwrites`` parameter can be used to create a 'secret'
        channel upon creation. This parameter expects a :class:`dict` of
        overwrites with the target (either a :class:`Member` or a :class:`Role`)
        as the key and a :class:`PermissionOverwrite` as the value.

        .. note::

            Creating a channel of a specified position will not update the position of
            other channels to follow suit. A follow-up call to :meth:`~TextChannel.edit`
            will be required to update the position of the channel in the channel list.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Examples
        ----------

        Creating a basic channel:

        .. code-block:: python3

            channel = await guild.create_text_channel('cool-channel')

        Creating a "secret" channel:

        .. code-block:: python3

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }

            channel = await guild.create_text_channel('secret', overwrites=overwrites)

        Parameters
        -----------
        name: :class:`str`
            The channel's name.
        overwrites: Dict[Union[:class:`Role`, :class:`Member`], :class:`PermissionOverwrite`]
            A :class:`dict` of target (either a role or a member) to
            :class:`PermissionOverwrite` to apply upon creation of a channel.
            Useful for creating secret channels.
        category: Optional[:class:`CategoryChannel`]
            The category to place the newly created channel under.
            The permissions will be automatically synced to category if no
            overwrites are provided.
        position: :class:`int`
            The position in the channel list. This is a number that starts
            at 0. e.g. the top channel is position 0.
        topic: :class:`str`
            The new channel's topic.
        slowmode_delay: :class:`int`
            Specifies the slowmode rate limit for user in this channel, in seconds.
            The maximum value possible is ``21600``.
        nsfw: :class:`bool`
            To mark the channel as NSFW or not.
        news: :class:`bool`
            Whether to create the text channel as a news channel.

            .. versionadded:: 2.0
        default_auto_archive_duration: :class:`int`
            The default auto archive duration for threads created in the text channel (in minutes).
            Must be one of ``60``, ``1440``, ``4320``, or ``10080``.

            .. versionadded:: 2.0
        default_thread_slowmode_delay: :class:`int`
            The default slowmode delay in seconds for threads created in the text channel.

            .. versionadded:: 2.0
        reason: Optional[:class:`str`]
            The reason for creating this channel. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have the proper permissions to create this channel.
        HTTPException
            Creating the channel failed.
        TypeError
            The permission overwrite information is not in proper form.

        Returns
        -------
        :class:`TextChannel`
            The channel that was just created.
        """

        options = {}
        if position is not MISSING:
            options['position'] = position

        if topic is not MISSING:
            options['topic'] = topic

        if slowmode_delay is not MISSING:
            options['rate_limit_per_user'] = slowmode_delay

        if nsfw is not MISSING:
            options['nsfw'] = nsfw

        if default_auto_archive_duration is not MISSING:
            options['default_auto_archive_duration'] = default_auto_archive_duration

        if default_thread_slowmode_delay is not MISSING:
            options['default_thread_rate_limit_per_user'] = default_thread_slowmode_delay

        data = await self._create_channel(
            name,
            overwrites=overwrites,
            channel_type=ChannelType.news if news else ChannelType.text,
            category=category,
            reason=reason,
            **options,
        )
        channel = TextChannel(state=self._state, guild=self, data=data)

        # temporarily add to the cache
        self._channels[channel.id] = channel
        return channel

    async def create_voice_channel(
        self,
        name: str,
        *,
        reason: Optional[str] = None,
        category: Optional[CategoryChannel] = None,
        position: int = MISSING,
        bitrate: int = MISSING,
        user_limit: int = MISSING,
        rtc_region: Optional[str] = MISSING,
        video_quality_mode: VideoQualityMode = MISSING,
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = MISSING,
        nsfw: bool = MISSING,
    ) -> VoiceChannel:
        """|coro|

        This is similar to :meth:`create_text_channel` except makes a :class:`VoiceChannel` instead.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        -----------
        name: :class:`str`
            The channel's name.
        overwrites: Dict[Union[:class:`Role`, :class:`Member`], :class:`PermissionOverwrite`]
            A :class:`dict` of target (either a role or a member) to
            :class:`PermissionOverwrite` to apply upon creation of a channel.
            Useful for creating secret channels.
        category: Optional[:class:`CategoryChannel`]
            The category to place the newly created channel under.
            The permissions will be automatically synced to category if no
            overwrites are provided.
        position: :class:`int`
            The position in the channel list. This is a number that starts
            at 0. e.g. the top channel is position 0.
        bitrate: :class:`int`
            The channel's preferred audio bitrate in bits per second.
        user_limit: :class:`int`
            The channel's limit for number of members that can be in a voice channel.
        rtc_region: Optional[:class:`str`]
            The region for the voice channel's voice communication.
            A value of ``None`` indicates automatic voice region detection.

            .. versionadded:: 1.7
        video_quality_mode: :class:`VideoQualityMode`
            The camera video quality for the voice channel's participants.

            .. versionadded:: 2.0
        nsfw: :class:`bool`
            To mark the channel as NSFW or not.

            .. versionadded:: 2.1
        reason: Optional[:class:`str`]
            The reason for creating this channel. Shows up on the audit log.

        Raises
        ------
        Forbidden
            You do not have the proper permissions to create this channel.
        HTTPException
            Creating the channel failed.
        TypeError
            The permission overwrite information is not in proper form.

        Returns
        -------
        :class:`VoiceChannel`
            The channel that was just created.
        """
        options = {}
        if position is not MISSING:
            options['position'] = position

        if bitrate is not MISSING:
            options['bitrate'] = bitrate

        if user_limit is not MISSING:
            options['user_limit'] = user_limit

        if rtc_region is not MISSING:
            options['rtc_region'] = None if rtc_region is None else rtc_region

        if video_quality_mode is not MISSING:
            if not isinstance(video_quality_mode, VideoQualityMode):
                raise TypeError('video_quality_mode must be of type VideoQualityMode')
            options['video_quality_mode'] = video_quality_mode.value

        if nsfw is not MISSING:
            options['nsfw'] = nsfw

        data = await self._create_channel(
            name, overwrites=overwrites, channel_type=ChannelType.voice, category=category, reason=reason, **options
        )
        channel = VoiceChannel(state=self._state, guild=self, data=data)

        # temporarily add to the cache
        self._channels[channel.id] = channel
        return channel

    async def create_stage_channel(
        self,
        name: str,
        *,
        reason: Optional[str] = None,
        category: Optional[CategoryChannel] = None,
        position: int = MISSING,
        bitrate: int = MISSING,
        user_limit: int = MISSING,
        rtc_region: Optional[str] = MISSING,
        video_quality_mode: VideoQualityMode = MISSING,
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = MISSING,
        nsfw: bool = MISSING,
    ) -> StageChannel:
        """|coro|

        This is similar to :meth:`create_text_channel` except makes a :class:`StageChannel` instead.

        .. versionadded:: 1.7

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        -----------
        name: :class:`str`
            The channel's name.
        overwrites: Dict[Union[:class:`Role`, :class:`Member`], :class:`PermissionOverwrite`]
            A :class:`dict` of target (either a role or a member) to
            :class:`PermissionOverwrite` to apply upon creation of a channel.
            Useful for creating secret channels.
        category: Optional[:class:`CategoryChannel`]
            The category to place the newly created channel under.
            The permissions will be automatically synced to category if no
            overwrites are provided.
        position: :class:`int`
            The position in the channel list. This is a number that starts
            at 0. e.g. the top channel is position 0.
        bitrate: :class:`int`
            The channel's preferred audio bitrate in bits per second.

            .. versionadded:: 2.0
        user_limit: :class:`int`
            The channel's limit for number of members that can be in a voice channel.

            .. versionadded:: 2.0
        rtc_region: Optional[:class:`str`]
            The region for the voice channel's voice communication.
            A value of ``None`` indicates automatic voice region detection.

            .. versionadded:: 2.0
        video_quality_mode: :class:`VideoQualityMode`
            The camera video quality for the voice channel's participants.

            .. versionadded:: 2.0
        nsfw: :class:`bool`
            To mark the channel as NSFW or not.

            .. versionadded:: 2.1
        reason: Optional[:class:`str`]
            The reason for creating this channel. Shows up on the audit log.

        Raises
        ------
        Forbidden
            You do not have the proper permissions to create this channel.
        HTTPException
            Creating the channel failed.
        TypeError
            The permission overwrite information is not in proper form.

        Returns
        -------
        :class:`StageChannel`
            The channel that was just created.
        """

        options = {}
        if position is not MISSING:
            options['position'] = position

        if bitrate is not MISSING:
            options['bitrate'] = bitrate

        if user_limit is not MISSING:
            options['user_limit'] = user_limit

        if rtc_region is not MISSING:
            options['rtc_region'] = None if rtc_region is None else rtc_region

        if video_quality_mode is not MISSING:
            if not isinstance(video_quality_mode, VideoQualityMode):
                raise TypeError('video_quality_mode must be of type VideoQualityMode')
            options['video_quality_mode'] = video_quality_mode.value

        if nsfw is not MISSING:
            options['nsfw'] = nsfw

        data = await self._create_channel(
            name,
            overwrites=overwrites,
            channel_type=ChannelType.stage_voice,
            category=category,
            reason=reason,
            **options,
        )
        channel = StageChannel(state=self._state, guild=self, data=data)

        # temporarily add to the cache
        self._channels[channel.id] = channel
        return channel

    async def create_category(
        self,
        name: str,
        *,
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = MISSING,
        reason: Optional[str] = None,
        position: int = MISSING,
    ) -> CategoryChannel:
        """|coro|

        Same as :meth:`create_text_channel` except makes a :class:`CategoryChannel` instead.

        .. note::

            The ``category`` parameter is not supported in this function since categories
            cannot have categories.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Raises
        ------
        Forbidden
            You do not have the proper permissions to create this channel.
        HTTPException
            Creating the channel failed.
        TypeError
            The permission overwrite information is not in proper form.

        Returns
        -------
        :class:`CategoryChannel`
            The channel that was just created.
        """
        options: Dict[str, Any] = {}
        if position is not MISSING:
            options['position'] = position

        data = await self._create_channel(
            name, overwrites=overwrites, channel_type=ChannelType.category, reason=reason, **options
        )
        channel = CategoryChannel(state=self._state, guild=self, data=data)

        # temporarily add to the cache
        self._channels[channel.id] = channel
        return channel

    create_category_channel = create_category

    async def create_directory(
        self,
        name: str,
        *,
        reason: Optional[str] = None,
        category: Optional[CategoryChannel] = None,
        position: int = MISSING,
        topic: str = MISSING,
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = MISSING,
    ) -> DirectoryChannel:
        """|coro|

        This is similar to :meth:`create_text_channel` except makes a :class:`DirectoryChannel` instead.

        The ``overwrites`` parameter can be used to create a 'secret'
        channel upon creation. This parameter expects a :class:`dict` of
        overwrites with the target (either a :class:`Member` or a :class:`Role`)
        as the key and a :class:`PermissionOverwrite` as the value.

        .. versionadded:: 2.1

        Parameters
        -----------
        name: :class:`str`
            The channel's name.
        overwrites: Dict[Union[:class:`Role`, :class:`Member`], :class:`PermissionOverwrite`]
            A :class:`dict` of target (either a role or a member) to
            :class:`PermissionOverwrite` to apply upon creation of a channel.
            Useful for creating secret channels.
        category: Optional[:class:`CategoryChannel`]
            The category to place the newly created channel under.
            The permissions will be automatically synced to category if no
            overwrites are provided.
        position: :class:`int`
            The position in the channel list. This is a number that starts
            at 0. e.g. the top channel is position 0.
        topic: :class:`str`
            The new channel's topic.
        reason: Optional[:class:`str`]
            The reason for creating this channel. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have the proper permissions to create this channel.
        HTTPException
            Creating the channel failed.
        TypeError
            The permission overwrite information is not in proper form.

        Returns
        -------
        :class:`TextChannel`
            The channel that was just created.
        """
        options = {}
        if position is not MISSING:
            options['position'] = position
        if topic is not MISSING:
            options['topic'] = topic

        data = await self._create_channel(
            name,
            overwrites=overwrites,
            channel_type=ChannelType.directory,
            category=category,
            reason=reason,
            **options,
        )
        channel = DirectoryChannel(state=self._state, guild=self, data=data)

        # temporarily add to the cache
        self._channels[channel.id] = channel
        return channel

    create_directory_channel = create_directory

    async def create_forum(
        self,
        name: str,
        *,
        topic: str = MISSING,
        position: int = MISSING,
        category: Optional[CategoryChannel] = None,
        slowmode_delay: int = MISSING,
        nsfw: bool = MISSING,
        media: bool = MISSING,
        overwrites: Mapping[Union[Role, Member, Object], PermissionOverwrite] = MISSING,
        reason: Optional[str] = None,
        default_auto_archive_duration: int = MISSING,
        default_thread_slowmode_delay: int = MISSING,
        default_sort_order: ForumOrderType = MISSING,
        default_reaction_emoji: EmojiInputType = MISSING,
        default_layout: ForumLayoutType = MISSING,
        available_tags: Sequence[ForumTag] = MISSING,
    ) -> ForumChannel:
        """|coro|

        Similar to :meth:`create_text_channel` except makes a :class:`ForumChannel` instead.

        The ``overwrites`` parameter can be used to create a 'secret'
        channel upon creation. This parameter expects a :class:`dict` of
        overwrites with the target (either a :class:`Member` or a :class:`Role`)
        as the key and a :class:`PermissionOverwrite` as the value.

        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`str`
            The channel's name.
        overwrites: Dict[Union[:class:`Role`, :class:`Member`], :class:`PermissionOverwrite`]
            A :class:`dict` of target (either a role or a member) to
            :class:`PermissionOverwrite` to apply upon creation of a channel.
            Useful for creating secret channels.
        topic: :class:`str`
            The channel's topic.
        category: Optional[:class:`CategoryChannel`]
            The category to place the newly created channel under.
            The permissions will be automatically synced to category if no
            overwrites are provided.
        position: :class:`int`
            The position in the channel list. This is a number that starts
            at 0. e.g. the top channel is position 0.
        nsfw: :class:`bool`
            To mark the channel as NSFW or not.
        slowmode_delay: :class:`int`
            Specifies the slowmode rate limit for users in this channel, in seconds.
            The maximum possible value is ``21600``.
        reason: Optional[:class:`str`]
            The reason for creating this channel. Shows up in the audit log.
        default_auto_archive_duration: :class:`int`
            The default auto archive duration for threads created in the forum channel (in minutes).
            Must be one of ``60``, ``1440``, ``4320``, or ``10080``.
        default_thread_slowmode_delay: :class:`int`
            The default slowmode delay in seconds for threads created in this forum.
        default_sort_order: :class:`ForumOrderType`
            The default sort order for posts in this forum channel.
        default_reaction_emoji: Union[:class:`Emoji`, :class:`PartialEmoji`, :class:`str`]
            The default reaction emoji for threads created in this forum to show in the
            add reaction button.
        default_layout: :class:`ForumLayoutType`
            The default layout for posts in this forum.
            This cannot be set if ``media`` is set to ``True``.
        available_tags: Sequence[:class:`ForumTag`]
            The available tags for this forum channel.
        media: :class:`bool`
            Whether to create a media forum channel.

            .. versionadded:: 2.1

        Raises
        -------
        Forbidden
            You do not have the proper permissions to create this channel.
        HTTPException
            Creating the channel failed.
        TypeError
            The permission overwrite information is not in proper form.

        Returns
        -------
        :class:`ForumChannel`
            The channel that was just created.
        """
        options = {}

        if position is not MISSING:
            options['position'] = position

        if topic is not MISSING:
            options['topic'] = topic

        if slowmode_delay is not MISSING:
            options['rate_limit_per_user'] = slowmode_delay

        if nsfw is not MISSING:
            options['nsfw'] = nsfw

        if default_auto_archive_duration is not MISSING:
            options['default_auto_archive_duration'] = default_auto_archive_duration

        if default_thread_slowmode_delay is not MISSING:
            options['default_thread_rate_limit_per_user'] = default_thread_slowmode_delay

        if default_sort_order is not MISSING:
            if not isinstance(default_sort_order, ForumOrderType):
                raise TypeError(
                    f'default_sort_order parameter must be a ForumOrderType not {default_sort_order.__class__.__name__}'
                )

            options['default_sort_order'] = default_sort_order.value

        if default_reaction_emoji is not MISSING:
            if isinstance(default_reaction_emoji, _EmojiTag):
                options['default_reaction_emoji'] = default_reaction_emoji._to_partial()._to_forum_tag_payload()
            elif isinstance(default_reaction_emoji, str):
                options['default_reaction_emoji'] = PartialEmoji.from_str(default_reaction_emoji)._to_forum_tag_payload()
            else:
                raise ValueError(f'default_reaction_emoji parameter must be either Emoji, PartialEmoji, or str')

        if not media and default_layout is not MISSING:
            if not isinstance(default_layout, ForumLayoutType):
                raise TypeError(
                    f'default_layout parameter must be a ForumLayoutType not {default_layout.__class__.__name__}'
                )

            options['default_forum_layout'] = default_layout.value

        if available_tags is not MISSING:
            options['available_tags'] = [t.to_dict() for t in available_tags]

        data = await self._create_channel(
            name=name,
            overwrites=overwrites,
            channel_type=ChannelType.forum if not media else ChannelType.media,
            category=category,
            reason=reason,
            **options,
        )

        channel = ForumChannel(
            state=self._state, guild=self, data=data  # pyright: ignore[reportArgumentType] # it's the correct data
        )

        # temporarily add to the cache
        self._channels[channel.id] = channel
        return channel

    create_forum_channel = create_forum

    async def leave(self) -> None:
        """|coro|

        Leaves the guild.

        .. note::

            You cannot leave a guild that you own, you must delete it instead
            via :meth:`delete`.

        Raises
        --------
        HTTPException
            Leaving the guild failed.
        """
        await self._state.http.leave_guild(self.id, lurking=not self.is_joined())

    async def delete(self) -> None:
        """|coro|

        Deletes the guild. You must be the guild owner to delete the
        guild.

        Raises
        --------
        HTTPException
            Deleting the guild failed.
        Forbidden
            You do not have permissions to delete the guild.
        """

        await self._state.http.delete_guild(self.id)

    async def edit(
        self,
        *,
        reason: Optional[str] = MISSING,
        name: str = MISSING,
        description: Optional[str] = MISSING,
        icon: Optional[bytes] = MISSING,
        banner: Optional[bytes] = MISSING,
        splash: Optional[bytes] = MISSING,
        discovery_splash: Optional[bytes] = MISSING,
        community: bool = MISSING,
        afk_channel: Optional[VoiceChannel] = MISSING,
        owner: Snowflake = MISSING,
        afk_timeout: int = MISSING,
        default_notifications: NotificationLevel = MISSING,
        verification_level: VerificationLevel = MISSING,
        explicit_content_filter: ContentFilter = MISSING,
        vanity_code: str = MISSING,
        system_channel: Optional[TextChannel] = MISSING,
        system_channel_flags: SystemChannelFlags = MISSING,
        preferred_locale: Locale = MISSING,
        rules_channel: Optional[TextChannel] = MISSING,
        public_updates_channel: Optional[TextChannel] = MISSING,
        safety_alerts_channel: Optional[TextChannel] = MISSING,
        premium_progress_bar_enabled: bool = MISSING,
        discoverable: bool = MISSING,
        invites_disabled: bool = MISSING,
        widget_enabled: bool = MISSING,
        widget_channel: Optional[Snowflake] = MISSING,
        mfa_level: MFALevel = MISSING,
        raid_alerts_disabled: bool = MISSING,
        invites_disabled_until: Optional[datetime] = MISSING,
        dms_disabled_until: Optional[datetime] = MISSING,
    ) -> Guild:
        r"""|coro|

        Edits the guild.

        You must have :attr:`~Permissions.manage_guild` to edit the guild.

        .. versionchanged:: 2.0
            The newly updated guild is returned.

        .. versionchanged:: 2.0
            The ``region`` keyword parameter has been removed.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` or
            :exc:`ValueError` instead of ``InvalidArgument``.

        Parameters
        ----------
        name: :class:`str`
            The new name of the guild.
        description: Optional[:class:`str`]
            The new description of the guild. Could be ``None`` for no description.
        icon: :class:`bytes`
            A :term:`py:bytes-like object` representing the icon. Only PNG/JPEG is supported.
            GIF is only available to guilds that contain ``ANIMATED_ICON`` in :attr:`Guild.features`.
            Could be ``None`` to denote removal of the icon.
        banner: :class:`bytes`
            A :term:`py:bytes-like object` representing the banner. Only PNG/JPEG is supported.
            GIF is only available to guilds that contain ``ANIMATED_BANNER`` in :attr:`Guild.features`.
            Could be ``None`` to denote removal of the banner.
            This is only available to guilds that contain ``BANNER`` in :attr:`Guild.features`.
        splash: :class:`bytes`
            A :term:`py:bytes-like object` representing the invite splash.
            Only PNG/JPEG supported. Could be ``None`` to denote removing the
            splash. This is only available to guilds that contain ``INVITE_SPLASH``
            in :attr:`Guild.features`.
        discovery_splash: :class:`bytes`
            A :term:`py:bytes-like object` representing the discovery splash.
            Only PNG/JPEG supported. Could be ``None`` to denote removing the
            splash. This is only available to guilds that contain ``DISCOVERABLE``
            in :attr:`Guild.features`.

            .. versionadded:: 2.0
        community: :class:`bool`
            Whether the guild should be a Community guild. If set to ``True``\, both ``rules_channel``
            and ``public_updates_channel`` parameters are required.

            .. versionadded:: 2.0
        afk_channel: Optional[:class:`VoiceChannel`]
            The new channel that is the AFK channel. Could be ``None`` for no AFK channel.
        afk_timeout: :class:`int`
            The number of seconds until someone is moved to the AFK channel.
        owner: :class:`Member`
            The new owner of the guild to transfer ownership to. Note that you must
            be owner of the guild to do this.
        verification_level: :class:`VerificationLevel`
            The new verification level for the guild.
        default_notifications: :class:`NotificationLevel`
            The new default notification level for the guild.
        explicit_content_filter: :class:`ContentFilter`
            The new explicit content filter for the guild.
        vanity_code: :class:`str`
            The new vanity code for the guild.
        system_channel: Optional[:class:`TextChannel`]
            The new channel that is used for the system channel. Could be ``None`` for no system channel.
        system_channel_flags: :class:`SystemChannelFlags`
            The new system channel settings to use with the new system channel.
        preferred_locale: :class:`Locale`
            The new preferred locale for the guild. Used as the primary language in the guild.

            .. versionchanged:: 2.0

                Now accepts an enum instead of :class:`str`.
        rules_channel: Optional[:class:`TextChannel`]
            The new channel that is used for rules. This is only available to
            guilds that contain ``COMMUNITY`` in :attr:`Guild.features`. Could be ``None`` for no rules
            channel.

            .. versionadded:: 1.4
        public_updates_channel: Optional[:class:`TextChannel`]
            The new channel that is used for public updates from Discord. This is only available to
            guilds that contain ``COMMUNITY`` in :attr:`Guild.features`. Could be ``None`` for no
            public updates channel.

            .. versionadded:: 1.4
        safety_alerts_channel: Optional[:class:`TextChannel`]
            The new channel that is used for safety alerts. This is only available to
            guilds that contain ``COMMUNITY`` in :attr:`Guild.features`. Could be ``None`` for no
            safety alerts channel.

            .. versionadded:: 2.1
        premium_progress_bar_enabled: :class:`bool`
            Whether the premium AKA server boost level progress bar should be enabled for the guild.

            .. versionadded:: 2.0
        discoverable: :class:`bool`
            Whether server discovery is enabled for this guild.

            .. versionadded:: 2.0
        invites_disabled: :class:`bool`
            Whether joining via invites should be disabled for the guild.

            .. versionadded:: 2.0
        widget_enabled: :class:`bool`
            Whether to enable the widget for the guild.

            .. versionadded:: 2.0
        widget_channel: Optional[:class:`abc.Snowflake`]
             The new widget channel. ``None`` removes the widget channel.

            .. versionadded:: 2.0
        mfa_level: :class:`MFALevel`
            The guild's new Multi-Factor Authentication requirement level.
            Note that you must be owner of the guild to do this.

            .. versionadded:: 2.0
        raid_alerts_disabled: :class:`bool`
            Whether the alerts for raid protection should be disabled for the guild.

            .. versionadded:: 2.1
        invites_disabled_until: Optional[:class:`datetime.datetime`]
            The time when invites should be enabled again, or ``None`` to disable the action.
            This must be a timezone-aware datetime object. Consider using :func:`utils.utcnow`.

            .. versionadded:: 2.1
        dms_disabled_until: Optional[:class:`datetime.datetime`]
            The time when direct messages should be allowed again, or ``None`` to disable the action.
            This must be a timezone-aware datetime object. Consider using :func:`utils.utcnow`.

            .. versionadded:: 2.1
        reason: Optional[:class:`str`]
            The reason for editing this guild. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have permissions to edit the guild.
        HTTPException
            Editing the guild failed.
        ValueError
            The image format passed in to ``icon`` is invalid. It must be
            PNG or JPG. This is also raised if you are not the owner of the
            guild and request an ownership transfer.
        TypeError
            The type passed to the ``default_notifications``, ``verification_level``,
            ``explicit_content_filter``, ``system_channel_flags``, or ``mfa_level`` parameter was
            of the incorrect type.

        Returns
        --------
        :class:`Guild`
            The newly updated guild. Note that this has the same limitations as
            mentioned in :meth:`Client.fetch_guild` and may not have full data.
        """
        http = self._state.http

        if vanity_code is not MISSING:
            await http.change_vanity_code(self.id, vanity_code, reason=reason)

        fields: Dict[str, Any] = {}
        if name is not MISSING:
            fields['name'] = name

        if description is not MISSING:
            fields['description'] = description

        if preferred_locale is not MISSING:
            fields['preferred_locale'] = str(preferred_locale)

        if afk_timeout is not MISSING:
            fields['afk_timeout'] = afk_timeout

        if icon is not MISSING:
            if icon is None:
                fields['icon'] = icon
            else:
                fields['icon'] = utils._bytes_to_base64_data(icon)

        if banner is not MISSING:
            if banner is None:
                fields['banner'] = banner
            else:
                fields['banner'] = utils._bytes_to_base64_data(banner)

        if splash is not MISSING:
            if splash is None:
                fields['splash'] = splash
            else:
                fields['splash'] = utils._bytes_to_base64_data(splash)

        if discovery_splash is not MISSING:
            if discovery_splash is None:
                fields['discovery_splash'] = discovery_splash
            else:
                fields['discovery_splash'] = utils._bytes_to_base64_data(discovery_splash)

        if default_notifications is not MISSING:
            if not isinstance(default_notifications, NotificationLevel):
                raise TypeError('default_notifications field must be of type NotificationLevel')
            fields['default_message_notifications'] = default_notifications.value

        if afk_channel is not MISSING:
            if afk_channel is None:
                fields['afk_channel_id'] = afk_channel
            else:
                fields['afk_channel_id'] = afk_channel.id

        if system_channel is not MISSING:
            if system_channel is None:
                fields['system_channel_id'] = system_channel
            else:
                fields['system_channel_id'] = system_channel.id

        if rules_channel is not MISSING:
            if rules_channel is None:
                fields['rules_channel_id'] = rules_channel
            else:
                fields['rules_channel_id'] = rules_channel.id

        if public_updates_channel is not MISSING:
            if public_updates_channel is None:
                fields['public_updates_channel_id'] = public_updates_channel
            else:
                fields['public_updates_channel_id'] = public_updates_channel.id

        if safety_alerts_channel is not MISSING:
            if safety_alerts_channel is None:
                fields['safety_alerts_channel_id'] = safety_alerts_channel
            else:
                fields['safety_alerts_channel_id'] = safety_alerts_channel.id

        if owner is not MISSING:
            if self.owner_id != self._state.self_id:
                raise ValueError('To transfer ownership you must be the owner of the guild')

            fields['owner_id'] = owner.id

        if verification_level is not MISSING:
            if not isinstance(verification_level, VerificationLevel):
                raise TypeError('verification_level field must be of type VerificationLevel')
            fields['verification_level'] = verification_level.value

        if explicit_content_filter is not MISSING:
            if not isinstance(explicit_content_filter, ContentFilter):
                raise TypeError('explicit_content_filter field must be of type ContentFilter')
            fields['explicit_content_filter'] = explicit_content_filter.value

        if system_channel_flags is not MISSING:
            if not isinstance(system_channel_flags, SystemChannelFlags):
                raise TypeError('system_channel_flags field must be of type SystemChannelFlags')
            fields['system_channel_flags'] = system_channel_flags.value

        if any(feat is not MISSING for feat in (community, discoverable, invites_disabled, raid_alerts_disabled)):
            features = set(self.features)

            if community is not MISSING:
                if community:
                    if 'rules_channel_id' in fields and 'public_updates_channel_id' in fields:
                        features.add('COMMUNITY')
                    else:
                        raise ValueError(
                            'community field requires both rules_channel and public_updates_channel fields to be provided'
                        )
                else:
                    features.discard('COMMUNITY')

            if discoverable is not MISSING:
                if discoverable:
                    features.add('DISCOVERABLE')
                else:
                    features.discard('DISCOVERABLE')

            if invites_disabled is not MISSING:
                if invites_disabled:
                    features.add('INVITES_DISABLED')
                else:
                    features.discard('INVITES_DISABLED')

            if raid_alerts_disabled is not MISSING:
                if raid_alerts_disabled:
                    features.add('RAID_ALERTS_DISABLED')
                else:
                    features.discard('RAID_ALERTS_DISABLED')

            fields['features'] = list(features)

        if premium_progress_bar_enabled is not MISSING:
            fields['premium_progress_bar_enabled'] = premium_progress_bar_enabled

        widget_payload: EditWidgetSettings = {}
        if widget_channel is not MISSING:
            widget_payload['channel_id'] = None if widget_channel is None else widget_channel.id
        if widget_enabled is not MISSING:
            widget_payload['enabled'] = widget_enabled

        if widget_payload:
            await self._state.http.edit_widget(self.id, payload=widget_payload, reason=reason)

        if mfa_level is not MISSING:
            if not isinstance(mfa_level, MFALevel):
                raise TypeError('mfa_level must be of type MFALevel')

            await http.edit_guild_mfa_level(self.id, mfa_level=mfa_level.value)

        incident_actions_payload: IncidentData = {}
        if invites_disabled_until is not MISSING:
            if invites_disabled_until is None:
                incident_actions_payload['invites_disabled_until'] = None
            else:
                if invites_disabled_until.tzinfo is None:
                    raise TypeError(
                        'invites_disabled_until must be an aware datetime. Consider using discord.utils.utcnow() or datetime.datetime.now().astimezone() for local time.'
                    )
                incident_actions_payload['invites_disabled_until'] = invites_disabled_until.isoformat()

        if dms_disabled_until is not MISSING:
            if dms_disabled_until is None:
                incident_actions_payload['dms_disabled_until'] = None
            else:
                if dms_disabled_until.tzinfo is None:
                    raise TypeError(
                        'dms_disabled_until must be an aware datetime. Consider using discord.utils.utcnow() or datetime.datetime.now().astimezone() for local time.'
                    )
                incident_actions_payload['dms_disabled_until'] = dms_disabled_until.isoformat()

        if incident_actions_payload:
            await http.edit_incident_actions(self.id, payload=incident_actions_payload)

        data = await http.edit_guild(self.id, reason=reason, **fields)
        return Guild(data=data, state=self._state)

    async def webhook_channels(self) -> List[Union[TextChannel, VoiceChannel, StageChannel, PartialMessageable]]:
        """|coro|

        Retrieves the channels that the current user can create webhooks in for the guild.

        .. versionadded:: 2.1

        Raises
        -------
        HTTPException
            Retrieving the webhook channels failed.

        Returns
        --------
        List[Union[:class:`TextChannel`, :class:`VoiceChannel`, :class:`StageChannel`, :class:`PartialMessageable`]]
            The channels that the current user can create webhooks in. Falls back to :class:`PartialMessageable` if the channel is not found in cache.
            Any :class:`PartialMessageable` will have its :attr:`PartialMessageable.name` filled in.
        """
        state = self._state
        data = await state.http.get_guild_webhook_channels(self.id)
        return [self.get_channel(int(c['id'])) or PartialMessageable._from_webhook_channel(self, c) for c in data]  # type: ignore

    async def fetch_channels(self) -> Sequence[GuildChannel]:
        """|coro|

        Retrieves all :class:`abc.GuildChannel` that the guild has.

        .. note::

            This method is an API call. For general usage, consider :attr:`channels` instead.

        .. versionadded:: 1.2

        Raises
        -------
        InvalidData
            An unknown channel type was received from Discord.
        HTTPException
            Retrieving the channels failed.

        Returns
        -------
        Sequence[:class:`abc.GuildChannel`]
            All channels in the guild.
        """
        data = await self._state.http.get_all_guild_channels(self.id)

        def convert(d):
            factory, ch_type = _guild_channel_factory(d['type'])
            if factory is None:
                raise InvalidData('Unknown channel type {type} for channel ID {id}.'.format_map(d))

            channel = factory(guild=self, state=self._state, data=d)
            return channel

        return [convert(d) for d in data]

    async def fetch_member(self, member_id: int, /) -> Member:
        """|coro|

        Retrieves a :class:`Member` from a guild ID, and a member ID.

        .. note::

            This method is an API call. If you have member cache, consider :meth:`get_member` instead.

        .. versionchanged:: 2.0

            ``member_id`` parameter is now positional-only.

        Parameters
        -----------
        member_id: :class:`int`
            The member's ID to fetch from.

        Raises
        -------
        Forbidden
            You do not have access to the guild.
        HTTPException
            Fetching the member failed.
        NotFound
            The member could not be found.

        Returns
        --------
        :class:`Member`
            The member from the member ID.
        """
        data = await self._state.http.get_member(self.id, member_id)
        return Member(data=data, state=self._state, guild=self)

    async def fetch_member_profile(
        self,
        member_id: int,
        /,
        *,
        with_mutual_guilds: bool = True,
        with_mutual_friends_count: bool = False,
        with_mutual_friends: bool = True,
    ) -> MemberProfile:
        """|coro|

        Retrieves a :class:`.MemberProfile` from a guild ID, and a member ID.

        .. versionadded:: 2.0

        Parameters
        ------------
        member_id: :class:`int`
            The ID of the member to fetch their profile for.
        with_mutual_guilds: :class:`bool`
            Whether to fetch mutual guilds.
            This fills in :attr:`.MemberProfile.mutual_guilds`.
        with_mutual_friends_count: :class:`bool`
            Whether to fetch the number of mutual friends.
            This fills in :attr:`.MemberProfile.mutual_friends_count`.
        with_mutual_friends: :class:`bool`
            Whether to fetch mutual friends.
            This fills in :attr:`.MemberProfile.mutual_friends` and :attr:`.MemberProfile.mutual_friends_count`.

        Raises
        -------
        NotFound
            A user with this ID does not exist.
            You do not have a mutual with this user and the user is not a bot.
        HTTPException
            Fetching the profile failed.
        InvalidData
            The member is not in this guild or has blocked you.

        Returns
        --------
        :class:`.MemberProfile`
            The profile of the member.
        """
        state = self._state
        data = await state.http.get_user_profile(
            member_id,
            self.id,
            with_mutual_guilds=with_mutual_guilds,
            with_mutual_friends_count=with_mutual_friends_count,
            with_mutual_friends=with_mutual_friends,
        )
        if 'guild_member_profile' not in data:
            raise InvalidData('Member is not in this guild')
        if 'guild_member' not in data:
            raise InvalidData('Member has blocked you')

        return MemberProfile(state=state, data=data, guild=self)

    async def fetch_ban(self, user: Snowflake) -> BanEntry:
        """|coro|

        Retrieves the :class:`BanEntry` for a user.

        You must have :attr:`~Permissions.ban_members` to get this information.

        Parameters
        -----------
        user: :class:`abc.Snowflake`
            The user to get ban information from.

        Raises
        ------
        Forbidden
            You do not have proper permissions to get the information.
        NotFound
            This user is not banned.
        HTTPException
            An error occurred while fetching the information.

        Returns
        -------
        :class:`BanEntry`
            The :class:`BanEntry` object for the specified user.
        """
        data = await self._state.http.get_ban(user.id, self.id)
        return BanEntry(user=User(state=self._state, data=data['user']), reason=data['reason'])

    async def fetch_channel(self, channel_id: int, /) -> Union[GuildChannel, Thread]:
        """|coro|

        Retrieves a :class:`.abc.GuildChannel` or :class:`.Thread` with the specified ID.

        .. note::

            This method is an API call. For general usage, consider :meth:`get_channel_or_thread` instead.

        .. versionadded:: 2.0

        Raises
        -------
        InvalidData
            An unknown channel type was received from Discord
            or the guild the channel belongs to is not the same
            as the one in this object points to.
        HTTPException
            Retrieving the channel failed.
        NotFound
            Invalid Channel ID.
        Forbidden
            You do not have permission to fetch this channel.

        Returns
        --------
        Union[:class:`.abc.GuildChannel`, :class:`.Thread`]
            The channel from the ID.
        """
        data = await self._state.http.get_channel(channel_id)

        factory, ch_type = _threaded_guild_channel_factory(data['type'])
        if factory is None:
            raise InvalidData('Unknown channel type {type} for channel ID {id}.'.format_map(data))

        if ch_type in (ChannelType.group, ChannelType.private):
            raise InvalidData('Channel ID resolved to a private channel')

        guild_id = int(data['guild_id'])  # type: ignore # channel won't be a private channel
        if self.id != guild_id:
            raise InvalidData('Guild ID resolved to a different guild')

        channel: GuildChannel = factory(guild=self, state=self._state, data=data)  # type: ignore # channel won't be a private channel
        return channel

    async def bans(
        self,
        *,
        limit: Optional[int] = 1000,
        before: Snowflake = MISSING,
        after: Snowflake = MISSING,
        paginate: bool = True,
    ) -> AsyncIterator[BanEntry]:
        """Retrieves an :term:`asynchronous iterator` of the users that are banned from the guild as a :class:`BanEntry`.

        You must have :attr:`~Permissions.ban_members` to get this information.

        .. versionchanged:: 2.0
            Due to a breaking change in Discord's API, this now returns a paginated iterator instead of a list.

        Examples
        ---------

        Usage ::

            async for entry in guild.bans(limit=150):
                print(entry.user, entry.reason)

        Flattening into a list ::

            bans = [entry async for entry in guild.bans(limit=2000)]
            # bans is now a list of BanEntry...

        All parameters are optional.

        Parameters
        -----------
        limit: Optional[:class:`int`]
            The number of bans to retrieve. If ``None``, it retrieves every ban in
            the guild. Note, however, that this would make it a slow operation.
            Defaults to ``1000``.
        before: :class:`.abc.Snowflake`
            Retrieves bans before this user.
        after: :class:`.abc.Snowflake`
            Retrieve bans after this user.
        paginate: :class:`bool`
            Whether to paginate the results. If ``False``, all bans are fetched with a single request and yielded,
            ``limit`` is ignored, and ``before`` and ``after`` must not be provided.

            .. versionadded:: 2.0

        Raises
        -------
        Forbidden
            You do not have proper permissions to get the information.
        HTTPException
            An error occurred while fetching the information.
        TypeError
            Both ``after`` and ``before`` were provided, as Discord does not
            support this type of pagination.

        Yields
        --------
        :class:`BanEntry`
            The ban entry of the banned user.
        """
        if before is not MISSING and after is not MISSING:
            raise TypeError('bans pagination does not support both before and after')

        # This endpoint paginates in ascending order
        _state = self._state
        endpoint = _state.http.get_bans

        if not paginate:
            # For user accounts, not providing a limit will return *every* ban,
            # as they were too lazy to implement proper pagination in the client
            # However, pagination may be wanted for guilds with massive ban lists
            data = await endpoint(self.id)
            for entry in data:
                yield BanEntry(user=User(state=_state, data=entry['user']), reason=entry['reason'])
            return

        async def _before_strategy(retrieve: int, before: Optional[Snowflake], limit: Optional[int]):
            before_id = before.id if before else None
            data = await endpoint(self.id, limit=retrieve, before=before_id)

            if data:
                if limit is not None:
                    limit -= len(data)

                before = Object(id=int(data[0]['user']['id']))

            return data, before, limit

        async def _after_strategy(retrieve: int, after: Optional[Snowflake], limit: Optional[int]):
            after_id = after.id if after else None
            data = await endpoint(self.id, limit=retrieve, after=after_id)

            if data:
                if limit is not None:
                    limit -= len(data)

                after = Object(id=int(data[-1]['user']['id']))

            return data, after, limit

        if before:
            strategy, state = _before_strategy, before
        else:
            strategy, state = _after_strategy, after

        while True:
            retrieve = 1000 if limit is None else min(limit, 1000)
            if retrieve < 1:
                return

            data, state, limit = await strategy(retrieve, state, limit)

            # Terminate loop on next iteration; there's no data left after this
            if len(data) < 1000:
                limit = 0

            for e in data:
                yield BanEntry(user=User(state=_state, data=e['user']), reason=e['reason'])

    def search(
        self,
        content: str = MISSING,
        *,
        limit: Optional[int] = 25,
        offset: int = 0,
        before: SnowflakeTime = MISSING,
        after: SnowflakeTime = MISSING,
        include_nsfw: bool = MISSING,
        channels: Collection[Snowflake] = MISSING,
        authors: Collection[Snowflake] = MISSING,
        author_types: Collection[MessageSearchAuthorType] = MISSING,
        mentions: Collection[Snowflake] = MISSING,
        mention_everyone: bool = MISSING,
        pinned: bool = MISSING,
        has: Collection[MessageSearchHasType] = MISSING,
        embed_types: Collection[EmbedType] = MISSING,
        embed_providers: Collection[str] = MISSING,
        link_hostnames: Collection[str] = MISSING,
        attachment_filenames: Collection[str] = MISSING,
        attachment_extensions: Collection[str] = MISSING,
        application_commands: Collection[Snowflake] = MISSING,
        oldest_first: bool = MISSING,
        most_relevant: bool = False,
    ) -> AsyncIterator[Message]:
        """Returns an :term:`asynchronous iterator` that enables searching the guild's messages.

        You must have :attr:`~Permissions.read_message_history` to do this.

        .. note::

            Due to a limitation with the Discord API, the :class:`.Message`
            objects returned by this method do not contain complete
            :attr:`.Message.reactions` data.

        .. versionadded:: 2.1

        Examples
        ---------

        Usage ::

            counter = 0
            async for message in guild.search('hi', limit=200):
                if message.author == client.user:
                    counter += 1

        Flattening into a list: ::

            messages = [message async for message in guild.search('test', limit=123)]
            # messages is now a list of Message...

        All parameters are optional.

        Parameters
        -----------
        content: :class:`str`
            The message content to search for.
        limit: Optional[:class:`int`]
            The number of messages to retrieve.
            If ``None``, retrieves every message in the results. Note, however,
            that this would make it a slow operation.
        offset: :class:`int`
            The pagination offset to start at.
        before: Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]
            Retrieve messages before this date or message.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.
        after: Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]
            Retrieve messages after this date or message.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.
        nsfw_allowed: :class:`bool`
            Whether to include messages from NSFW channels. Defaults to :attr:`~discord.ClientUser.nsfw_allowed`.
        channels: List[Union[:class:`abc.GuildChannel`, :class:`abc.PrivateChannel`, :class:`Thread`]]
            The channels to filter by.
        authors: List[:class:`User`]
            The authors to filter by.
        author_types: List[:class:`str`]
            The author types to filter by. Can be one of ``user``, ``bot``, or ``webhook``.
            These can be negated by prefixing with ``-``, which will exclude them.
        mentions: List[:class:`User`]
            The mentioned users to filter by.
        mention_everyone: :class:`bool`
            Whether to filter by messages that do or do not mention @everyone.
        pinned: :class:`bool`
            Whether to filter by messages that are or are not pinned.
        has: List[:class:`str`]
            The message attributes to filter by. Can be one of ``image``, ``sound``,
            ``video``, ``file``, ``sticker``, ``embed``, or ``link``. These can be
            negated by prefixing with ``-``, which will exclude them.
        embed_types: List[:class:`str`]
            The embed types to filter by.
        embed_providers: List[:class:`str`]
            The embed providers to filter by (e.g. tenor).
        link_hostnames: List[:class:`str`]
            The link hostnames to filter by (e.g. google.com).
        attachment_filenames: List[:class:`str`]
            The attachment filenames to filter by.
        attachment_extensions: List[:class:`str`]
            The attachment extensions to filter by (e.g. txt).
        application_commands: List[:class:`abc.ApplicationCommand`]
            The used application commands to filter by.
        oldest_first: :class:`bool`
            Whether to return the oldest results first. Defaults to ``True`` if
            ``before`` is specified, otherwise ``False``. Ignored when ``most_relevant`` is set.
        most_relevant: :class:`bool`
            Whether to sort the results by relevance. Limits pagination to 9975 entries.

        Raises
        ------
        ~discord.HTTPException
            The request to search messages failed.
        TypeError
            Provided both ``before`` and ``after`` when ``most_relevant`` is set.
        ValueError
            Could not resolve the channel's guild ID.

        Yields
        -------
        :class:`Message`
            The message with the message data parsed.
        """
        return abc._handle_message_search(
            self,
            limit=limit,
            offset=offset,
            before=before,
            after=after,
            content=content,
            include_nsfw=include_nsfw,
            channels=channels,
            authors=authors,
            author_types=author_types,
            mentions=mentions,
            mention_everyone=mention_everyone,
            pinned=pinned,
            has=has,
            embed_types=embed_types,
            embed_providers=embed_providers,
            link_hostnames=link_hostnames,
            attachment_filenames=attachment_filenames,
            attachment_extensions=attachment_extensions,
            application_commands=application_commands,
            oldest_first=oldest_first,
            most_relevant=most_relevant,
        )

    async def prune_members(
        self,
        *,
        days: int,
        compute_prune_count: bool = True,
        roles: Collection[Snowflake] = MISSING,
        reason: Optional[str] = None,
    ) -> Optional[int]:
        r"""|coro|

        Prunes the guild from its inactive members.

        The inactive members are denoted if they have not logged on in
        ``days`` number of days and they have no roles.

        You must have both :attr:`~Permissions.kick_members` and :attr:`~Permissions.manage_guild` to do this.

        To check how many members you would prune without actually pruning,
        see the :meth:`estimate_pruned_members` function.

        To prune members that have specific roles see the ``roles`` parameter.

        .. versionchanged:: 1.4
            The ``roles`` keyword-only parameter was added.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        -----------
        days: :class:`int`
            The number of days before counting as inactive.
        reason: Optional[:class:`str`]
            The reason for doing this action. Shows up on the audit log.
        compute_prune_count: :class:`bool`
            Whether to compute the prune count. This defaults to ``True``
            which makes it prone to timeouts in very large guilds. In order
            to prevent timeouts, you must set this to ``False``. If this is
            set to ``False``\, then this function will always return ``None``.
        roles: List[:class:`abc.Snowflake`]
            A list of :class:`abc.Snowflake` that represent roles to include in the pruning process. If a member
            has a role that is not specified, they'll be excluded.

        Raises
        -------
        Forbidden
            You do not have permissions to prune members.
        HTTPException
            An error occurred while pruning members.
        TypeError
            An integer was not passed for ``days``.

        Returns
        ---------
        Optional[:class:`int`]
            The number of members pruned. If ``compute_prune_count`` is ``False``
            then this returns ``None``.
        """
        if not isinstance(days, int):
            raise TypeError(f'Expected int for ``days``, received {days.__class__.__name__} instead')

        if roles:
            role_ids = [str(role.id) for role in roles]
        else:
            role_ids = []

        data = await self._state.http.prune_members(
            self.id, days, compute_prune_count=compute_prune_count, roles=role_ids, reason=reason
        )
        return data['pruned']

    async def templates(self) -> List[Template]:
        """|coro|

        Gets the list of templates from this guild.

        You must have :attr:`~.Permissions.manage_guild` to do this.

        .. versionadded:: 1.7

        Raises
        -------
        Forbidden
            You don't have permissions to get the templates.

        Returns
        --------
        List[:class:`Template`]
            The templates for this guild.
        """
        from .template import Template

        data = await self._state.http.guild_templates(self.id)
        return [Template(data=d, state=self._state) for d in data]

    async def webhooks(self) -> List[Webhook]:
        """|coro|

        Gets the list of webhooks from this guild.

        You must have :attr:`~.Permissions.manage_webhooks` to do this.

        Raises
        -------
        Forbidden
            You don't have permissions to get the webhooks.

        Returns
        --------
        List[:class:`Webhook`]
            The webhooks for this guild.
        """
        from .webhook import Webhook

        data = await self._state.http.guild_webhooks(self.id)
        return [Webhook.from_state(d, state=self._state) for d in data]

    async def estimate_pruned_members(self, *, days: int, roles: Collection[Snowflake] = MISSING) -> Optional[int]:
        """|coro|

        Similar to :meth:`prune_members` except instead of actually
        pruning members, it returns how many members it would prune
        from the guild had it been called.

        .. versionchanged:: 2.0
            The returned value can be ``None``.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        -----------
        days: :class:`int`
            The number of days before counting as inactive.
        roles: List[:class:`abc.Snowflake`]
            A list of :class:`abc.Snowflake` that represent roles to include in the estimate. If a member
            has a role that is not specified, they'll be excluded.

            .. versionadded:: 1.7

        Raises
        -------
        Forbidden
            You do not have permissions to prune members.
        HTTPException
            An error occurred while fetching the prune members estimate.
        TypeError
            An integer was not passed for ``days``.

        Returns
        ---------
        Optional[:class:`int`]
            The number of members estimated to be pruned.
        """
        if not isinstance(days, int):
            raise TypeError(f'Expected int for ``days``, received {days.__class__.__name__} instead')

        if roles:
            role_ids = [str(role.id) for role in roles]
        else:
            role_ids = []

        data = await self._state.http.estimate_pruned_members(self.id, days, role_ids)
        return data['pruned']

    async def invites(self) -> List[Invite]:
        """|coro|

        Returns a list of all active instant invites from the guild.

        You must have :attr:`~Permissions.manage_guild` to get this information.

        Raises
        -------
        Forbidden
            You do not have proper permissions to get the information.
        HTTPException
            An error occurred while fetching the information.

        Returns
        -------
        List[:class:`Invite`]
            The list of invites that are currently active.
        """
        data = await self._state.http.invites_from(self.id)
        result = []
        for invite in data:
            channel = self.get_channel(int(invite['channel']['id']))  # type: ignore
            result.append(Invite(state=self._state, data=invite, guild=self, channel=channel))

        return result

    async def create_template(self, *, name: str, description: str = MISSING) -> Template:
        """|coro|

        Creates a template for the guild.

        You must have :attr:`~Permissions.manage_guild` to do this.

        .. versionadded:: 1.7

        Parameters
        -----------
        name: :class:`str`
            The name of the template.
        description: :class:`str`
            The description of the template.

        Returns
        --------
        :class:`Template`
            The created template.
        """
        from .template import Template

        payload = {'name': name}

        if description:
            payload['description'] = description

        data = await self._state.http.create_template(self.id, payload)

        return Template(state=self._state, data=data)

    async def create_integration(self, *, type: IntegrationType, id: Union[str, int], reason: Optional[str] = None) -> None:
        """|coro|

        Attaches an integration to the guild.

        You must have :attr:`~Permissions.manage_guild` to do this.

        .. versionadded:: 1.4

        Parameters
        -----------
        type: :class:`str`
            The integration type (``twitch`` or ``youtube``).
        id: :class:`str`
            The integration account ID.
        reason: Optional[:class:`str`]
            The reason for creating this integration. Shows up on the audit log.

            .. versionadded:: 2.0

        Raises
        -------
        Forbidden
            You do not have permission to create the integration.
        HTTPException
            The account could not be found.
        """
        await self._state.http.create_integration(self.id, type, id, reason=reason)

    async def integrations(self, *, has_commands: bool = False) -> List[Integration]:
        """|coro|

        Returns a list of all integrations attached to the guild.

        You must have :attr:`~Permissions.manage_guild` to do this.

        .. versionadded:: 1.4

        Parameters
        -----------
        has_commands: :class:`bool`
            Whether to only return integrations that have commands registered.

            .. versionadded:: 2.1

        Raises
        -------
        Forbidden
            You do not have permission to create the integration.
        HTTPException
            Fetching the integrations failed.

        Returns
        --------
        List[:class:`Integration`]
            The list of integrations that are attached to the guild.
        """
        data = await self._state.http.get_all_integrations(self.id, has_commands=has_commands)

        def convert(d):
            factory, _ = _integration_factory(d['type'])
            return factory(guild=self, data=d)

        return [convert(d) for d in data]

    async def application_commands(self) -> List[Union[SlashCommand, UserCommand, MessageCommand]]:
        """|coro|

        Returns a list of all application commands available in the guild.

        .. versionadded:: 2.1

        .. note::

            Commands that the user does not have permission to use will not be returned.

        Raises
        -------
        HTTPException
            Fetching the commands failed.

        Returns
        --------
        List[Union[:class:`SlashCommand`, :class:`UserCommand`, :class:`MessageCommand`]]
            The list of application commands that are available in the guild.
        """
        state = self._state
        data = await state.http.guild_application_command_index(self.id)
        cmds = data['application_commands']
        apps = {int(app['id']): state.create_integration_application(app) for app in data.get('applications') or []}

        result = []
        for cmd in cmds:
            _, cls = _command_factory(cmd['type'])
            application = apps.get(int(cmd['application_id']))
            result.append(cls(state=state, data=cmd, application=application))
        return result

    async def fetch_stickers(self) -> List[GuildSticker]:
        r"""|coro|

        Retrieves a list of all :class:`Sticker`\s for the guild.

        .. versionadded:: 2.0

        .. note::

            This method is an API call. For general usage, consider :attr:`stickers` instead.

        Raises
        ---------
        HTTPException
            An error occurred fetching the stickers.

        Returns
        --------
        List[:class:`GuildSticker`]
            The retrieved stickers.
        """
        data = await self._state.http.get_all_guild_stickers(self.id)
        return [GuildSticker(state=self._state, data=d) for d in data]

    async def fetch_sticker(self, sticker_id: int, /) -> GuildSticker:
        """|coro|

        Retrieves a custom :class:`Sticker` from the guild.

        .. versionadded:: 2.0

        .. note::

            This method is an API call.
            For general usage, consider iterating over :attr:`stickers` instead.

        Parameters
        -------------
        sticker_id: :class:`int`
            The sticker's ID.

        Raises
        ---------
        NotFound
            The sticker requested could not be found.
        HTTPException
            An error occurred fetching the sticker.

        Returns
        --------
        :class:`GuildSticker`
            The retrieved sticker.
        """
        data = await self._state.http.get_guild_sticker(self.id, sticker_id)
        return GuildSticker(state=self._state, data=data)

    async def create_sticker(
        self,
        *,
        name: str,
        description: str,
        emoji: str,
        file: File,
        reason: Optional[str] = None,
    ) -> GuildSticker:
        """|coro|

        Creates a :class:`Sticker` for the guild.

        You must have :attr:`~Permissions.manage_emojis_and_stickers` to do this.

        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`str`
            The sticker name. Must be at least 2 characters.
        description: :class:`str`
            The sticker's description.
        emoji: :class:`str`
            The name of a unicode emoji that represents the sticker's expression.
        file: :class:`File`
            The file of the sticker to upload.
        reason: :class:`str`
            The reason for creating this sticker. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You are not allowed to create stickers.
        HTTPException
            An error occurred creating a sticker.

        Returns
        --------
        :class:`GuildSticker`
            The created sticker.
        """
        payload = {
            'name': name,
            'description': description or '',
        }

        try:
            emoji = unicodedata.name(emoji)
        except TypeError:
            pass
        else:
            emoji = emoji.replace(' ', '_')

        payload['tags'] = emoji

        data = await self._state.http.create_guild_sticker(self.id, payload, file, reason)
        return self._state.store_sticker(self, data)

    async def delete_sticker(self, sticker: Snowflake, /, *, reason: Optional[str] = None) -> None:
        """|coro|

        Deletes the custom :class:`Sticker` from the guild.

        You must have :attr:`~Permissions.manage_emojis_and_stickers` to do this.

        .. versionadded:: 2.0

        Parameters
        -----------
        sticker: :class:`abc.Snowflake`
            The sticker you are deleting.
        reason: Optional[:class:`str`]
            The reason for deleting this sticker. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You are not allowed to delete stickers.
        HTTPException
            An error occurred deleting the sticker.
        """
        await self._state.http.delete_guild_sticker(self.id, sticker.id, reason)

    async def subscribed_scheduled_events(self) -> List[Union[ScheduledEvent, Object]]:
        """|coro|

        Retrieves a list of all scheduled events that the current user is subscribed to.

        .. versionadded:: 2.1

        Raises
        -------
        HTTPException
            Retrieving the subscribed scheduled events failed.

        Returns
        --------
        List[Union[:class:`ScheduledEvent`, :class:`Object`]]
            The subscribed scheduled events. Falls back to an object if the event is not found in cache.
        """
        data = await self._state.http.get_subscribed_scheduled_events(self.id)
        return [
            self.get_scheduled_event(int(d['guild_scheduled_event_id'])) or Object(id=int(d['guild_scheduled_event_id']))
            for d in data
        ]

    async def fetch_scheduled_events(self, *, with_counts: bool = True) -> List[ScheduledEvent]:
        """|coro|

        Retrieves a list of all scheduled events for the guild.

        .. versionadded:: 2.0

        Parameters
        ------------
        with_counts: :class:`bool`
            Whether to include the number of users that are subscribed to the event.
            Defaults to ``True``.

        Raises
        -------
        HTTPException
            Retrieving the scheduled events failed.

        Returns
        --------
        List[:class:`ScheduledEvent`]
            The scheduled events.
        """
        data = await self._state.http.get_scheduled_events(self.id, with_counts)
        return [ScheduledEvent(state=self._state, data=d) for d in data]

    async def fetch_scheduled_event(self, scheduled_event_id: int, /, *, with_counts: bool = True) -> ScheduledEvent:
        """|coro|

        Retrieves a scheduled event from the guild.

        .. versionadded:: 2.0

        Parameters
        ------------
        scheduled_event_id: :class:`int`
            The scheduled event ID.
        with_counts: :class:`bool`
            Whether to include the number of users that are subscribed to the event.
            Defaults to ``True``.

        Raises
        -------
        NotFound
            The scheduled event was not found.
        HTTPException
            Retrieving the scheduled event failed.

        Returns
        --------
        :class:`ScheduledEvent`
            The scheduled event.
        """
        data = await self._state.http.get_scheduled_event(self.id, scheduled_event_id, with_counts)
        return ScheduledEvent(state=self._state, data=data)

    @overload
    async def create_scheduled_event(
        self,
        *,
        name: str,
        start_time: datetime,
        entity_type: Literal[EntityType.external] = ...,
        privacy_level: PrivacyLevel = ...,
        location: str = ...,
        end_time: datetime = ...,
        description: str = ...,
        image: bytes = ...,
        directory_broadcast: bool = ...,
        reason: Optional[str] = ...,
    ) -> ScheduledEvent:
        ...

    @overload
    async def create_scheduled_event(
        self,
        *,
        name: str,
        start_time: datetime,
        entity_type: Literal[EntityType.stage_instance, EntityType.voice] = ...,
        privacy_level: PrivacyLevel = ...,
        channel: Snowflake = ...,
        end_time: datetime = ...,
        description: str = ...,
        image: bytes = ...,
        directory_broadcast: bool = ...,
        reason: Optional[str] = ...,
    ) -> ScheduledEvent:
        ...

    @overload
    async def create_scheduled_event(
        self,
        *,
        name: str,
        start_time: datetime,
        privacy_level: PrivacyLevel = ...,
        location: str = ...,
        end_time: datetime = ...,
        description: str = ...,
        image: bytes = ...,
        directory_broadcast: bool = ...,
        reason: Optional[str] = ...,
    ) -> ScheduledEvent:
        ...

    @overload
    async def create_scheduled_event(
        self,
        *,
        name: str,
        start_time: datetime,
        privacy_level: PrivacyLevel = ...,
        channel: Union[VoiceChannel, StageChannel] = ...,
        end_time: datetime = ...,
        description: str = ...,
        image: bytes = ...,
        directory_broadcast: bool = ...,
        reason: Optional[str] = ...,
    ) -> ScheduledEvent:
        ...

    async def create_scheduled_event(
        self,
        *,
        name: str,
        start_time: datetime,
        entity_type: EntityType = MISSING,
        privacy_level: PrivacyLevel = PrivacyLevel.guild_only,
        channel: Optional[Snowflake] = MISSING,
        location: str = MISSING,
        end_time: datetime = MISSING,
        description: str = MISSING,
        image: bytes = MISSING,
        directory_broadcast: bool = False,
        reason: Optional[str] = None,
    ) -> ScheduledEvent:
        r"""|coro|

        Creates a scheduled event for the guild.

        You must have :attr:`~Permissions.manage_events` to do this.

        .. versionadded:: 2.0

        Parameters
        ------------
        name: :class:`str`
            The name of the scheduled event.
        description: :class:`str`
            The description of the scheduled event.
        channel: Optional[:class:`abc.Snowflake`]
            The channel to send the scheduled event to. If the channel is
            a :class:`StageInstance` or :class:`VoiceChannel` then
            it automatically sets the entity type.

            Required if ``entity_type`` is either :attr:`EntityType.voice` or
            :attr:`EntityType.stage_instance`.
        start_time: :class:`datetime.datetime`
            The scheduled start time of the scheduled event. This must be a timezone-aware
            datetime object. Consider using :func:`utils.utcnow`.
        end_time: :class:`datetime.datetime`
            The scheduled end time of the scheduled event. This must be a timezone-aware
            datetime object. Consider using :func:`utils.utcnow`.

            Required if the entity type is :attr:`EntityType.external`.
        privacy_level: :class:`PrivacyLevel`
            The privacy level of the scheduled event.
        entity_type: :class:`EntityType`
            The entity type of the scheduled event. If the channel is a
            :class:`StageInstance` or :class:`VoiceChannel` then this is
            automatically set to the appropriate entity type. If no channel
            is passed then the entity type is assumed to be
            :attr:`EntityType.external`
        image: :class:`bytes`
            The image of the scheduled event.
        location: :class:`str`
            The location of the scheduled event.

            Required if the ``entity_type`` is :attr:`EntityType.external`.
        directory_broadcast: :class:`bool`
            Whether to broadcast the scheduled event to the directories the guild is in.
            You should first check eligibility with :meth:`directory_broadcast_eligibility`.

            .. versionadded:: 2.1
        reason: Optional[:class:`str`]
            The reason for creating this scheduled event. Shows up on the audit log.

        Raises
        -------
        TypeError
            ``image`` was not a :term:`py:bytes-like object`, or ``privacy_level``
            was not a :class:`PrivacyLevel`, or ``entity_type`` was not an
            :class:`EntityType`, ``status`` was not an :class:`EventStatus`,
            or an argument was provided that was incompatible with the provided
            ``entity_type``.
        ValueError
            ``start_time`` or ``end_time`` was not a timezone-aware datetime object.
        Forbidden
            You are not allowed to create scheduled events.
        HTTPException
            Creating the scheduled event failed.

        Returns
        --------
        :class:`ScheduledEvent`
            The created scheduled event.
        """
        payload: Dict[str, Any] = {
            'name': name,
            'privacy_level': int(privacy_level or PrivacyLevel.guild_only.value),
            'broadcast_to_directory_channels': directory_broadcast,
        }
        metadata = {}

        if start_time.tzinfo is None:
            raise ValueError(
                'start_time must be an aware datetime. Consider using discord.utils.utcnow() or datetime.datetime.now().astimezone() for local time.'
            )
        payload['scheduled_start_time'] = start_time.isoformat()

        if privacy_level:
            if not isinstance(privacy_level, PrivacyLevel):
                raise TypeError('privacy_level must be of type PrivacyLevel')
        payload['privacy_level'] = (privacy_level or PrivacyLevel.guild_only).value

        entity_type = entity_type or getattr(channel, '_scheduled_event_entity_type', MISSING)
        if entity_type is MISSING:
            if channel and isinstance(channel, Object):
                if channel.type is VoiceChannel:
                    entity_type = EntityType.voice
                elif channel.type is StageChannel:
                    entity_type = EntityType.stage_instance
            elif location not in (MISSING, None):
                entity_type = EntityType.external
        else:
            if not isinstance(entity_type, EntityType):
                raise TypeError('entity_type must be of type EntityType')

            payload['entity_type'] = entity_type.value

        if entity_type is None:
            raise TypeError(
                f'invalid GuildChannel type passed; must be VoiceChannel or StageChannel not {channel.__class__.__name__}'
            )

        if description is not MISSING:
            payload['description'] = description

        if image is not MISSING:
            image_as_str: str = utils._bytes_to_base64_data(image)
            payload['image'] = image_as_str

        if entity_type in (EntityType.stage_instance, EntityType.voice):
            if channel in (MISSING, None):
                raise TypeError('channel must be set when entity_type is voice or stage_instance')

            payload['channel_id'] = channel.id

            if location is not MISSING:
                raise TypeError('location cannot be set when entity_type is voice or stage_instance')
        else:
            if channel is not MISSING:
                raise TypeError('channel cannot be set when entity_type is external')

            if location is MISSING or location is None:
                raise TypeError('location must be set when entity_type is external')

            metadata['location'] = location

            if not end_time:
                raise TypeError('end_time must be set when entity_type is external')

        if end_time:
            if end_time.tzinfo is None:
                raise ValueError(
                    'end_time must be an aware datetime. Consider using discord.utils.utcnow() or datetime.datetime.now().astimezone() for local time.'
                )
            payload['scheduled_end_time'] = end_time.isoformat()

        if metadata:
            payload['entity_metadata'] = metadata

        data = await self._state.http.create_guild_scheduled_event(self.id, **payload, reason=reason)
        return ScheduledEvent(state=self._state, data=data)

    async def top_emojis(self) -> List[Union[Emoji, PartialEmoji]]:
        """|coro|

        Retrieves the most used custom emojis in the guild. Emojis are returned in order of descending usage.

        .. versionadded:: 2.0

        Raises
        -------
        HTTPException
            Retrieving the top emojis failed.

        Returns
        --------
        List[Union[:class:`Emoji`, :class:`PartialEmoji`]]
            The most used emojis. Falls back to a bare :class:`PartialEmoji` if the emoji is not found in cache.
        """
        state = self._state
        data = await state.http.get_top_emojis(self.id)
        return [
            self._state.get_emoji(int(e['emoji_id'])) or PartialEmoji.with_state(state, name='', id=int(e['emoji_id']))
            for e in data['items']
        ]

    async def fetch_emojis(self) -> List[Emoji]:
        r"""|coro|

        Retrieves all custom :class:`Emoji`\s from the guild.

        .. note::

            This method is an API call. For general usage, consider :attr:`emojis` instead.

        Raises
        ---------
        HTTPException
            An error occurred fetching the emojis.

        Returns
        --------
        List[:class:`Emoji`]
            The retrieved emojis.
        """
        data = await self._state.http.get_all_custom_emojis(self.id)
        return [Emoji(guild=self, state=self._state, data=d) for d in data]

    async def fetch_emoji(self, emoji_id: int, /) -> Emoji:
        """|coro|

        Retrieves a custom :class:`Emoji` from the guild.

        .. note::

            This method is an API call.
            For general usage, consider iterating over :attr:`emojis` instead.

        .. versionchanged:: 2.0

            ``emoji_id`` parameter is now positional-only.

        Parameters
        -------------
        emoji_id: :class:`int`
            The emoji's ID.

        Raises
        ---------
        NotFound
            The emoji requested could not be found.
        HTTPException
            An error occurred fetching the emoji.

        Returns
        --------
        :class:`Emoji`
            The retrieved emoji.
        """
        data = await self._state.http.get_custom_emoji(self.id, emoji_id)
        return Emoji(guild=self, state=self._state, data=data)

    async def create_custom_emoji(
        self,
        *,
        name: str,
        image: bytes,
        roles: Collection[Role] = MISSING,
        reason: Optional[str] = None,
    ) -> Emoji:
        r"""|coro|

        Creates a custom :class:`Emoji` for the guild.

        There is currently a limit of 50 static and animated emojis respectively per guild,
        unless the guild has the ``MORE_EMOJI`` feature which extends the limit to 200.

        You must have :attr:`~Permissions.manage_emojis` to do this.

        Parameters
        -----------
        name: :class:`str`
            The emoji name. Must be at least 2 characters.
        image: :class:`bytes`
            The :term:`py:bytes-like object` representing the image data to use.
            Only JPG, PNG and GIF images are supported.
        roles: List[:class:`Role`]
            A :class:`list` of :class:`Role`\s that can use this emoji. Leave empty to make it available to everyone.
        reason: Optional[:class:`str`]
            The reason for creating this emoji. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You are not allowed to create emojis.
        HTTPException
            An error occurred creating an emoji.

        Returns
        --------
        :class:`Emoji`
            The created emoji.
        """
        img = utils._bytes_to_base64_data(image)
        if roles:
            role_ids: SnowflakeList = [role.id for role in roles]
        else:
            role_ids = []

        data = await self._state.http.create_custom_emoji(self.id, name, img, roles=role_ids, reason=reason)
        return self._state.store_emoji(self, data)

    async def delete_emoji(self, emoji: Snowflake, /, *, reason: Optional[str] = None) -> None:
        """|coro|

        Deletes the custom :class:`Emoji` from the guild.

        You must have :attr:`~Permissions.manage_emojis` to do this.

        .. versionchanged:: 2.0

            ``emoji`` parameter is now positional-only.

        Parameters
        -----------
        emoji: :class:`abc.Snowflake`
            The emoji you are deleting.
        reason: Optional[:class:`str`]
            The reason for deleting this emoji. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You are not allowed to delete emojis.
        HTTPException
            An error occurred deleting the emoji.
        """
        await self._state.http.delete_custom_emoji(self.id, emoji.id, reason=reason)

    async def fetch_roles(self) -> List[Role]:
        """|coro|

        Retrieves all :class:`Role` that the guild has.

        .. note::

            This method is an API call. For general usage, consider :attr:`roles` instead.

        .. versionadded:: 1.3

        Raises
        -------
        HTTPException
            Retrieving the roles failed.

        Returns
        -------
        List[:class:`Role`]
            All roles in the guild.
        """
        data = await self._state.http.get_roles(self.id)
        return [Role(guild=self, state=self._state, data=d) for d in data]

    async def fetch_role(self, role_id: int, /) -> Role:
        """|coro|

        Retrieves a :class:`Role` with the specified ID.

        .. versionadded:: 2.1

        .. note::

            This method is an API call. For general usage, consider :attr:`get_role` instead.

        Parameters
        ----------
        role_id: :class:`int`
            The role's ID.

        Raises
        -------
        NotFound
            The role requested could not be found.
        HTTPException
            An error occurred fetching the role.

        Returns
        -------
        :class:`Role`
            The retrieved role.
        """
        data = await self._state.http.get_role(self.id, role_id)
        return Role(guild=self, state=self._state, data=data)

    @overload
    async def create_role(
        self,
        *,
        reason: Optional[str] = ...,
        name: str = ...,
        permissions: Permissions = ...,
        colour: Union[Colour, int] = ...,
        hoist: bool = ...,
        mentionable: bool = ...,
        icon: Optional[bytes] = ...,
        emoji: Optional[PartialEmoji] = ...,
        secondary_colour: Optional[Union[Colour, int]] = ...,
        tertiary_colour: Optional[Union[Colour, int]] = ...,
    ) -> Role:
        ...

    @overload
    async def create_role(
        self,
        *,
        reason: Optional[str] = ...,
        name: str = ...,
        permissions: Permissions = ...,
        color: Union[Colour, int] = ...,
        hoist: bool = ...,
        display_icon: Union[bytes, str] = MISSING,
        mentionable: bool = ...,
        secondary_color: Optional[Union[Colour, int]] = ...,
        tertiary_color: Optional[Union[Colour, int]] = ...,
    ) -> Role:
        ...

    async def create_role(
        self,
        *,
        name: str = MISSING,
        permissions: Permissions = MISSING,
        color: Union[Colour, int] = MISSING,
        colour: Union[Colour, int] = MISSING,
        hoist: bool = MISSING,
        display_icon: Union[bytes, str] = MISSING,
        mentionable: bool = MISSING,
        icon: Optional[bytes] = MISSING,
        emoji: Optional[PartialEmoji] = MISSING,
        reason: Optional[str] = None,
        secondary_color: Optional[Union[Colour, int]] = MISSING,
        tertiary_color: Optional[Union[Colour, int]] = MISSING,
        secondary_colour: Optional[Union[Colour, int]] = MISSING,
        tertiary_colour: Optional[Union[Colour, int]] = MISSING,
    ) -> Role:
        """|coro|

        Creates a :class:`Role` for the guild.

        All fields are optional.

        You must have :attr:`~Permissions.manage_roles` to do this.

        .. versionchanged:: 1.6
            Can now pass ``int`` to ``colour`` keyword-only parameter.

        .. versionadded:: 2.0
            The ``display_icon`` keyword-only parameter was added.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        -----------
        name: :class:`str`
            The role name. Defaults to 'new role'.
        permissions: :class:`Permissions`
            The permissions to have. Defaults to no permissions.
        colour: Union[:class:`Colour`, :class:`int`]
            The colour for the role. Defaults to :meth:`Colour.default`.
            This is aliased to ``color`` as well.
        secondary_colour: Optional[Union[:class:`Colour`, :class:`int`]]
            The secondary colour for the role.

            .. versionadded:: 2.1
        tertiary_colour: Optional[Union[:class:`Colour`, :class:`int`]]
            The tertiary colour for the role. Can only be used for the holographic role preset,
            which is ``(11127295, 16759788, 16761760)``

            .. versionadded:: 2.1
        hoist: :class:`bool`
            Indicates if the role should be shown separately in the member list.
            Defaults to ``False``.
        display_icon: Union[:class:`bytes`, :class:`str`]
            A :term:`py:bytes-like object` representing the icon
            or :class:`str` representing unicode emoji that should be used as a role icon.
            Only PNG/JPEG is supported.
            This is only available to guilds that contain ``ROLE_ICONS`` in :attr:`features`.
        mentionable: :class:`bool`
            Indicates if the role should be mentionable by others.
            Defaults to ``False``.
        icon: Optional[:class:`bytes`]
            A :term:`py:bytes-like object` representing the icon. Only PNG/JPEG is supported.
            Could be ``None`` to denote removal of the icon.
        emoji: Optional[:class:`PartialEmoji`]
            An emoji to show next to the role. Only unicode emojis are supported.
        reason: Optional[:class:`str`]
            The reason for creating this role. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have permissions to create the role.
        HTTPException
            Creating the role failed.
        TypeError
            An invalid keyword argument was given.
        ValueError
            unicode_emoji was the wrong type.

        Returns
        --------
        :class:`Role`
            The newly created role.
        """
        fields: Dict[str, Any] = {}
        if permissions is not MISSING:
            fields['permissions'] = str(permissions.value)
        else:
            fields['permissions'] = '0'

        colours: Dict[str, Any] = {}

        actual_colour = colour or color or Colour.default()
        if isinstance(actual_colour, int):
            colours['primary_color'] = actual_colour
        else:
            colours['primary_color'] = actual_colour.value

        actual_secondary_colour = secondary_colour or secondary_color
        actual_tertiary_colour = tertiary_colour or tertiary_color

        if actual_secondary_colour is not MISSING:
            if actual_secondary_colour is None:
                colours['secondary_color'] = None
            elif isinstance(actual_secondary_colour, int):
                colours['secondary_color'] = actual_secondary_colour
            else:
                colours['secondary_color'] = actual_secondary_colour.value

        if actual_tertiary_colour is not MISSING:
            if actual_tertiary_colour is None:
                colours['tertiary_color'] = None
            elif isinstance(actual_tertiary_colour, int):
                colours['tertiary_color'] = actual_tertiary_colour
            else:
                colours['tertiary_color'] = actual_tertiary_colour.value

        fields['colors'] = colours

        if hoist is not MISSING:
            fields['hoist'] = hoist

        if display_icon is not MISSING:
            if isinstance(display_icon, bytes):
                fields['icon'] = utils._bytes_to_base64_data(display_icon)
            else:
                fields['unicode_emoji'] = display_icon

        if mentionable is not MISSING:
            fields['mentionable'] = mentionable

        if name is not MISSING:
            fields['name'] = name

        if icon is not MISSING:
            if icon is None:
                fields['icon'] = icon
            else:
                fields['icon'] = utils._bytes_to_base64_data(icon)

        if emoji is not MISSING:
            if emoji is None:
                fields['unicode_emoji'] = None
            elif emoji.id is not None:
                raise ValueError('emoji only supports unicode emojis')
            else:
                fields['unicode_emoji'] = emoji.name

        data = await self._state.http.create_role(self.id, reason=reason, **fields)
        role = Role(guild=self, data=data, state=self._state)

        return role

    async def edit_role_positions(self, positions: Mapping[Snowflake, int], *, reason: Optional[str] = None) -> List[Role]:
        """|coro|

        Bulk edits a list of :class:`Role` in the guild.

        You must have :attr:`~Permissions.manage_roles` to do this.

        .. versionadded:: 1.4

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Example
        ----------

        .. code-block:: python3

            positions = {
                bots_role: 1, # penultimate role
                tester_role: 2,
                admin_role: 6
            }

            await guild.edit_role_positions(positions=positions)

        Parameters
        -----------
        positions
            A :class:`dict` of :class:`Role` to :class:`int` to change the positions
            of each given role.
        reason: Optional[:class:`str`]
            The reason for editing the role positions. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have permissions to move the roles.
        HTTPException
            Moving the roles failed.
        TypeError
            An invalid keyword argument was given.

        Returns
        --------
        List[:class:`Role`]
            A list of all the roles in the guild.
        """
        if not isinstance(positions, Mapping):
            raise TypeError('positions parameter expects a dict')

        role_positions = []
        for role, position in positions.items():
            payload: RolePositionUpdatePayload = {'id': role.id, 'position': position}

            role_positions.append(payload)

        data = await self._state.http.move_role_position(self.id, role_positions, reason=reason)
        roles: List[Role] = []
        for d in data:
            role = Role(guild=self, data=d, state=self._state)
            roles.append(role)
            self._roles[role.id] = role

        return roles

    async def role_member_counts(self) -> Dict[Role, int]:
        """|coro|

        Retrieves the number of members in each role the guild has.

        .. versionadded:: 2.1

        Raises
        -------
        Forbidden
            You do not have permissions to get the member counts.
        HTTPException
            Getting the member counts failed.

        Returns
        --------
        Dict[:class:`Role`, :class:`int`]
            A mapping of the role to the number of members in that role.
        """
        data = await self._state.http.get_role_member_counts(self.id)
        ret: Dict[Role, int] = {}
        for k, v in data.items():
            role = self.get_role(int(k))
            if role is not None:
                ret[role] = v
        return ret

    async def kick(self, user: Snowflake, *, reason: Optional[str] = None) -> None:
        """|coro|

        Kicks a user from the guild.

        The user must meet the :class:`abc.Snowflake` abc.

        You must have :attr:`~Permissions.kick_members` to do this.

        Parameters
        -----------
        user: :class:`abc.Snowflake`
            The user to kick from the guild.
        reason: Optional[:class:`str`]
            The reason the user got kicked.

        Raises
        -------
        Forbidden
            You do not have the proper permissions to kick.
        HTTPException
            Kicking failed.
        """
        await self._state.http.kick(user.id, self.id, reason=reason)

    async def ban(
        self,
        user: Snowflake,
        *,
        reason: Optional[str] = None,
        delete_message_days: int = MISSING,
        delete_message_seconds: int = MISSING,
    ) -> None:
        """|coro|

        Bans a user from the guild.

        The user must meet the :class:`abc.Snowflake` abc.

        You must have :attr:`~Permissions.ban_members` to do this.

        Parameters
        -----------
        user: :class:`abc.Snowflake`
            The user to ban from the guild.
        delete_message_days: :class:`int`
            The number of days worth of messages to delete from the user
            in the guild. The minimum is 0 and the maximum is 7.
            Defaults to 1 day if neither ``delete_message_days`` nor
            ``delete_message_seconds`` are passed.

            .. deprecated:: 2.0
        delete_message_seconds: :class:`int`
            The number of seconds worth of messages to delete from the user
            in the guild. The minimum is 0 and the maximum is 604800 (7 days).
            Defaults to 1 day if neither ``delete_message_days`` nor
            ``delete_message_seconds`` are passed.

            .. versionadded:: 2.0
        reason: Optional[:class:`str`]
            The reason the user got banned.

        Raises
        -------
        NotFound
            The requested user was not found.
        Forbidden
            You do not have the proper permissions to ban.
        HTTPException
            Banning failed.
        TypeError
            You specified both ``delete_message_days`` and ``delete_message_seconds``.
        """
        if delete_message_days is not MISSING and delete_message_seconds is not MISSING:
            raise TypeError('Cannot mix delete_message_days and delete_message_seconds keyword arguments.')

        if delete_message_days is not MISSING:
            msg = 'delete_message_days is deprecated, use delete_message_seconds instead'
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            delete_message_seconds = delete_message_days * 86400  # one day

        if delete_message_seconds is MISSING:
            delete_message_seconds = 86400  # one day

        await self._state.http.ban(user.id, self.id, delete_message_seconds, reason=reason)

    async def unban(self, user: Snowflake, *, reason: Optional[str] = None) -> None:
        """|coro|

        Unbans a user from the guild.

        The user must meet the :class:`abc.Snowflake` abc.

        You must have :attr:`~Permissions.ban_members` to do this.

        Parameters
        -----------
        user: :class:`abc.Snowflake`
            The user to unban.
        reason: Optional[:class:`str`]
            The reason for doing this action. Shows up on the audit log.

        Raises
        -------
        NotFound
            The requested unban was not found.
        Forbidden
            You do not have the proper permissions to unban.
        HTTPException
            Unbanning failed.
        """
        await self._state.http.unban(user.id, self.id, reason=reason)

    async def bulk_ban(
        self,
        users: Iterable[Snowflake],
        *,
        reason: Optional[str] = None,
        delete_message_seconds: int = 86400,
    ) -> BulkBanResult:
        """|coro|

        Bans multiple users from the guild.

        The users must meet the :class:`abc.Snowflake` abc.

        You must have :attr:`~Permissions.ban_members` and :attr:`~Permissions.manage_guild` to do this.

        .. versionadded:: 2.1

        Parameters
        -----------
        users: Iterable[:class:`abc.Snowflake`]
            The users to ban from the guild, up to 200 users.
        delete_message_seconds: :class:`int`
            The number of seconds worth of messages to delete from the user
            in the guild. The minimum is 0 and the maximum is 604800 (7 days).
            Defaults to 1 day.
        reason: Optional[:class:`str`]
            The reason the users got banned.

        Raises
        -------
        Forbidden
            You do not have the proper permissions to ban.
        HTTPException
            Banning failed.

        Returns
        --------
        :class:`BulkBanResult`
            The result of the bulk ban operation.
        """

        response = await self._state.http.bulk_ban(
            self.id,
            user_ids=[u.id for u in users],
            delete_message_seconds=delete_message_seconds,
            reason=reason,
        )
        return BulkBanResult(
            banned=[Object(id=int(user_id), type=User) for user_id in response.get('banned_users', []) or []],
            failed=[Object(id=int(user_id), type=User) for user_id in response.get('failed_users', []) or []],
        )

    @property
    def vanity_url(self) -> Optional[str]:
        """Optional[:class:`str`]: The Discord vanity invite URL for this guild, if available.

        .. versionadded:: 2.0
        """
        if self.vanity_url_code is None:
            return None
        return f'{Invite.BASE}/{self.vanity_url_code}'

    async def vanity_invite(self) -> Optional[Invite]:
        """|coro|

        Returns the guild's special vanity invite.

        The guild must have ``VANITY_URL`` in :attr:`~Guild.features`.

        You must have :attr:`~Permissions.manage_guild` to do this as well.

        Raises
        -------
        Forbidden
            You do not have the proper permissions to get this.
        HTTPException
            Retrieving the vanity invite failed.

        Returns
        --------
        Optional[:class:`Invite`]
            The special vanity invite. If ``None`` then the guild does not
            have a vanity invite set.
        """
        # We start with { code: abc }
        payload = await self._state.http.get_vanity_code(self.id)
        if not payload['code']:
            return

        # Get the vanity channel & uses
        data = await self._state.http.get_invite(payload['code'])

        channel = self.get_channel(int(data['channel']['id']))  # type: ignore
        data.update({'temporary': False, 'max_uses': 0, 'max_age': 0, 'uses': payload.get('uses', 0)})  # type: ignore
        return Invite(state=self._state, data=payload, guild=self, channel=channel)  # type: ignore # We're faking a payload here

    async def audit_logs(
        self,
        *,
        limit: Optional[int] = 100,
        before: SnowflakeTime = MISSING,
        after: SnowflakeTime = MISSING,
        oldest_first: bool = MISSING,
        user: Snowflake = MISSING,
        action: AuditLogAction = MISSING,
    ) -> AsyncIterator[AuditLogEntry]:
        """Returns an :term:`asynchronous iterator` that enables receiving the guild's audit logs.

        You must have :attr:`~Permissions.view_audit_log` to do this.

        Examples
        ----------

        Getting the first 100 entries: ::

            async for entry in guild.audit_logs(limit=100):
                print(f'{entry.user} did {entry.action} to {entry.target}')

        Getting entries for a specific action: ::

            async for entry in guild.audit_logs(action=discord.AuditLogAction.ban):
                print(f'{entry.user} banned {entry.target}')

        Getting entries made by a specific user: ::

            entries = [entry async for entry in guild.audit_logs(limit=None, user=guild.me)]
            await channel.send(f'I made {len(entries)} moderation actions.')

        Parameters
        -----------
        limit: Optional[:class:`int`]
            The number of entries to retrieve. If ``None`` retrieve all entries.
        before: Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]
            Retrieve entries before this date or entry.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.
        after: Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]
            Retrieve entries after this date or entry.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.
        oldest_first: :class:`bool`
            If set to ``True``, return entries in oldest->newest order. Defaults to ``True`` if
            ``after`` is specified, otherwise ``False``.
        user: :class:`abc.Snowflake`
            The moderator to filter entries from.
        action: :class:`AuditLogAction`
            The action to filter with.

        Raises
        -------
        Forbidden
            You are not allowed to fetch audit logs
        HTTPException
            An error occurred while fetching the audit logs.

        Yields
        --------
        :class:`AuditLogEntry`
            The audit log entry.
        """

        async def _before_strategy(retrieve: int, before: Optional[Snowflake], limit: Optional[int]):
            before_id = before.id if before else None
            data = await self._state.http.get_audit_logs(
                self.id, limit=retrieve, user_id=user_id, action_type=action_type, before=before_id
            )

            entries = data.get('audit_log_entries', [])

            if data and entries:
                if limit is not None:
                    limit -= len(data)

                before = Object(id=int(entries[-1]['id']))

            return data, entries, before, limit

        async def _after_strategy(retrieve: int, after: Optional[Snowflake], limit: Optional[int]):
            after_id = after.id if after else None
            data = await self._state.http.get_audit_logs(
                self.id, limit=retrieve, user_id=user_id, action_type=action_type, after=after_id
            )

            entries = data.get('audit_log_entries', [])

            if data and entries:
                if limit is not None:
                    limit -= len(data)

                after = Object(id=int(entries[-1]['id']))

            return data, entries, after, limit

        if user is not MISSING:
            user_id = user.id
        else:
            user_id = None

        if action is not MISSING:
            action_type: Optional[AuditLogEvent] = action.value
        else:
            action_type = None

        if isinstance(before, datetime):
            before = Object(id=utils.time_snowflake(before, high=False))
        if isinstance(after, datetime):
            after = Object(id=utils.time_snowflake(after, high=True))

        if oldest_first:
            if after is MISSING:
                after = OLDEST_OBJECT

        predicate = None

        if oldest_first:
            strategy, state = _after_strategy, after
            if before:
                predicate = lambda m: int(m['id']) < before.id
        else:
            strategy, state = _before_strategy, before
            if after:
                predicate = lambda m: int(m['id']) > after.id

        # Circular import
        from .webhook import Webhook

        while True:
            retrieve = 100 if limit is None else min(limit, 100)
            if retrieve < 1:
                return

            data, raw_entries, state, limit = await strategy(retrieve, state, limit)

            if predicate:
                raw_entries = filter(predicate, raw_entries)

            users = (User(data=raw_user, state=self._state) for raw_user in data.get('users', []))
            user_map = {user.id: user for user in users}

            integrations = (Integration(data=raw_i, guild=self) for raw_i in data.get('integrations', []))
            integration_map = {integration.id: integration for integration in integrations}

            automod_rules = (
                AutoModRule(data=raw_rule, guild=self, state=self._state)
                for raw_rule in data.get('auto_moderation_rules', [])
            )
            automod_rule_map = {rule.id: rule for rule in automod_rules}

            webhooks = (Webhook.from_state(data=raw_webhook, state=self._state) for raw_webhook in data.get('webhooks', []))
            webhook_map = {webhook.id: webhook for webhook in webhooks}

            count = 0

            for count, raw_entry in enumerate(raw_entries, 1):
                # Weird Discord quirk
                if raw_entry['action_type'] is None:
                    continue

                yield AuditLogEntry(
                    data=raw_entry,
                    users=user_map,
                    integrations=integration_map,
                    automod_rules=automod_rule_map,
                    webhooks=webhook_map,
                    guild=self,
                )

            if count < 100:
                # There's no data left after this
                break

    async def ack(self) -> None:
        """|coro|

        Marks every message in this guild as read.

        Raises
        -------
        HTTPException
            Acking failed.
        """
        return await self._state.http.ack_guild(self.id)

    async def widget(self) -> Widget:
        """|coro|

        Returns the widget of the guild.

        .. note::

            The guild must have the widget enabled to get this information.

        Raises
        -------
        Forbidden
            The widget for this guild is disabled.
        HTTPException
            Retrieving the widget failed.

        Returns
        --------
        :class:`Widget`
            The guild's widget.
        """
        data = await self._state.http.get_widget(self.id)

        return Widget(state=self._state, data=data)

    async def edit_widget(
        self,
        *,
        enabled: bool = MISSING,
        channel: Optional[Snowflake] = MISSING,
        reason: Optional[str] = None,
    ) -> None:
        """|coro|

        Edits the widget of the guild. This can also be done with :attr:`~Guild.edit`.

        You must have :attr:`~Permissions.manage_guild` to do this.

        .. versionadded:: 2.0

        Parameters
        -----------
        enabled: :class:`bool`
            Whether to enable the widget for the guild.
        channel: Optional[:class:`~discord.abc.Snowflake`]
            The new widget channel. ``None`` removes the widget channel.
        reason: Optional[:class:`str`]
            The reason for editing this widget. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have permission to edit the widget.
        HTTPException
            Editing the widget failed.
        """
        payload: EditWidgetSettings = {}
        if channel is not MISSING:
            payload['channel_id'] = None if channel is None else channel.id
        if enabled is not MISSING:
            payload['enabled'] = enabled

        if payload:
            await self._state.http.edit_widget(self.id, payload=payload, reason=reason)

    async def welcome_screen(self) -> WelcomeScreen:
        """|coro|

        Returns the guild's welcome screen.

        You must have :attr:`~Permissions.manage_guild` permission to use this.

        .. note::

            The guild must have the welcome screen enabled to get this information.

        .. versionadded:: 2.0

        Raises
        -------
        NotFound
            The guild does not have a welcome screen.
        Forbidden
            You do not have :attr:`~Permissions.manage_guild`.
        HTTPException
            Retrieving the welcome screen failed.

        Returns
        --------
        :class:`WelcomeScreen`
            The welcome screen.
        """
        data = await self._state.http.get_welcome_screen(self.id)
        return WelcomeScreen(data=data, guild=self)

    async def edit_welcome_screen(
        self,
        *,
        description: str = MISSING,
        welcome_channels: Sequence[WelcomeChannel] = MISSING,
        enabled: bool = MISSING,
        reason: Optional[str] = None,
    ):
        """|coro|

        Edit the welcome screen.

        Welcome channels can only accept custom emojis if :attr:`Guild.premium_tier` is level 2 or above.

        You must have :attr:`~Permissions.manage_guild` in the guild to do this.

        All parameters are optional.

        .. versionadded:: 2.0

        Usage: ::

            rules_channel = guild.get_channel(12345678)
            announcements_channel = guild.get_channel(87654321)

            custom_emoji = utils.get(guild.emojis, name='loudspeaker')

            await welcome_screen.edit(
                description='This is a very cool community server!',
                welcome_channels=[
                    WelcomeChannel(channel=rules_channel, description='Read the rules!', emoji='👨‍🏫'),
                    WelcomeChannel(channel=announcements_channel, description='Watch out for announcements!', emoji=custom_emoji),
                ]
            )

        Parameters
        ------------
        enabled: :class:`bool`
            Whether the welcome screen will be shown.
        description: :class:`str`
            The welcome screen's description.
        welcome_channels: Optional[List[:class:`WelcomeChannel`]]
            The welcome channels (in order).
        reason: Optional[:class:`str`]
            The reason for editing the welcome screen. Shows up on the audit log.

        Raises
        -------
        NotFound
            The guild does not have a welcome screen.
        HTTPException
            Editing the welcome screen failed failed.
        Forbidden
            You don't have permissions to edit the welcome screen.
        """
        payload = {}

        if enabled is not MISSING:
            payload['enabled'] = enabled
        if description is not MISSING:
            payload['description'] = description
        if welcome_channels is not MISSING:
            channels = [channel._to_dict() for channel in welcome_channels] if welcome_channels else []
            payload['welcome_channels'] = channels

        if payload:
            await self._state.http.edit_welcome_screen(self.id, payload, reason=reason)

    async def applications(
        self, *, with_team: bool = False, type: Optional[ApplicationType] = None, channel: Optional[Snowflake] = None
    ) -> List[PartialApplication]:
        """|coro|

        Returns the list of applications that are attached to this guild.

        .. versionadded:: 2.0

        Parameters
        -----------
        with_team: :class:`bool`
            Whether to include the team of the application.
        type: :class:`ApplicationType`
            The type of application to restrict the returned applications to.

        Raises
        -------
        HTTPException
            Fetching the applications failed.

        Returns
        --------
        List[:class:`PartialApplication`]
            The applications that belong to this guild.
        """
        data = await self._state.http.get_guild_applications(
            self.id,
            include_team=with_team,
            type=int(type) if type else None,
            channel_id=channel.id if channel else None,
        )
        return [PartialApplication(state=self._state, data=app) for app in data]

    async def premium_subscriptions(self) -> List[PremiumGuildSubscription]:
        """|coro|

        Returns the list of premium subscriptions (boosts) for this guild.

        .. versionadded:: 2.0

        Raises
        -------
        Forbidden
            You do not have permission to get the premium guild subscriptions.
        HTTPException
            Fetching the premium guild subscriptions failed.

        Returns
        --------
        List[:class:`PremiumGuildSubscription`]
            The premium guild subscriptions.
        """
        data = await self._state.http.get_guild_subscriptions(self.id)
        return [PremiumGuildSubscription(state=self._state, data=sub) for sub in data]

    async def apply_premium_subscription_slots(self, *subscription_slots: Snowflake) -> List[PremiumGuildSubscription]:
        r"""|coro|

        Applies premium subscription slots to the guild (boosts the guild).

        .. versionadded:: 2.0

        Parameters
        -----------
        \*subscription_slots: :class:`PremiumGuildSubscriptionSlot`
            The subscription slots to apply.

        Raises
        -------
        HTTPException
            Applying the premium subscription slots failed.
        """
        if not subscription_slots:
            return []

        state = self._state
        data = await state.http.apply_guild_subscription_slots(self.id, [slot.id for slot in subscription_slots])
        return [PremiumGuildSubscription(state=state, data=sub) for sub in data]

    async def entitlements(
        self,
        *,
        with_sku: bool = True,
        with_application: bool = True,
        include_ended: bool = True,
        include_deleted: bool = True,
        entitlement_type: Optional[EntitlementType] = None,
    ) -> List[Entitlement]:
        """|coro|

        Returns the list of entitlements for this guild.

        .. versionadded:: 2.0

        Parameters
        -----------
        with_sku: :class:`bool`
            Whether to include the SKU information in the returned entitlements.
        with_application: :class:`bool`
            Whether to include the application in the returned entitlements' SKUs.
        include_ended: :class:`bool`
            Whether to include ended entitlements.

            .. versionadded:: 2.1
        include_deleted: :class:`bool`
            Whether to exclude deleted entitlements.

            .. versionchanged:: 2.1

                Renamed from ``exclude_consumed`` to ``include_consumed``.
        entitlement_type: Optional[:class:`.EntitlementType`]
            The type of entitlement to retrieve. If ``None`` then all entitlements are returned.

            .. versionadded:: 2.1

        Raises
        -------
        HTTPException
            Retrieving the entitlements failed.

        Returns
        -------
        List[:class:`Entitlement`]
            The guild's entitlements.
        """
        state = self._state
        data = await state.http.get_guild_entitlements(
            self.id,
            with_sku=with_sku,
            with_application=with_application,
            exclude_ended=not include_ended,
            exclude_deleted=not include_deleted,
            entitlement_type=int(entitlement_type) if entitlement_type else None,
        )
        return [Entitlement(state=state, data=d) for d in data]

    async def price_tiers(self) -> List[int]:
        """|coro|

        Returns the list of price tiers available for use in this guild.

        .. versionadded:: 2.0

        Raises
        -------
        HTTPException
            Fetching the price tiers failed.

        Returns
        --------
        List[:class:`int`]
            The available price tiers.
        """
        return await self._state.http.get_price_tiers(1, self.id)

    async def fetch_price_tier(self, price_tier: int, /) -> Dict[str, int]:
        """|coro|

        Returns a mapping of currency to price for the given price tier.

        .. versionadded:: 2.0

        Parameters
        -----------
        price_tier: :class:`int`
            The price tier to retrieve.

        Raises
        -------
        NotFound
            The price tier does not exist.
        HTTPException
            Fetching the price tier failed.

        Returns
        -------
        Dict[:class:`str`, :class:`int`]
            The price tier mapping.
        """
        return await self._state.http.get_price_tier(price_tier)

    async def chunk(self, *, cache: bool = True) -> List[Member]:
        """|coro|

        Requests all members that belong to this guild.

        This is a websocket operation and can be slow.

        .. versionadded:: 2.0

        .. note::

            For guilds with more than 1,000 members, this requires the
            :attr:`~Permissions.manage_roles`, :attr:`~Permissions.kick_members`,
            or :attr:`~Permissions.ban_members` permissions.
            For guilds with less than 1,000 members, this requires at least
            one channel that is viewable by every member.

        Parameters
        -----------
        cache: :class:`bool`
            Whether to cache the members as well.

        Raises
        -------
        ClientException
            This guild is not subscribed to.
            This guild cannot be chunked or chunking failed.
        InvalidData
            Did not receive a response from the Gateway.

        Returns
        --------
        List[:class:`Member`]
            The members that belong to this guild.
        """
        state = self._state
        if state.is_guild_evicted(self):
            return []
        if not state.subscriptions.is_subscribed(self):
            raise ClientException('This guild is not subscribed to')

        if await state._can_chunk_guild(self):
            members = await state.chunk_guild(self, cache=cache)
        elif not self._offline_members_hidden:
            members = await state.scrape_guild(self, cache=cache, chunk=True)
        else:
            raise ClientException('This guild cannot be chunked')

        return members

    async def fetch_members(
        self,
        channels: List[Snowflake] = MISSING,
        *,
        cache: bool = False,
        force_scraping: bool = False,
        delay: float = 0,
    ) -> List[Member]:
        """|coro|

        Retrieves all members that belong to this guild.
        This is a websocket operation and can be slow.

        This does not enable you to receive events for the guild, and can be called multiple times.

        .. versionadded:: 2.0

        .. note::

            If you have any of :attr:`~Permissions.kick_members`, :attr:`~Permissions.ban_members`,
            or :attr:`~Permissions.manage_roles`, members will be requested normally (including offline members).
            Else, this will scrape the member sidebar, which is slower and may not include offline members.

        Parameters
        -----------
        channels: List[:class:`~abc.Snowflake`]
            A list of up to 5 channels to request members from. More channels make it faster.
            This only applies when scraping from the member sidebar.
        cache: :class:`bool`
            Whether to cache the members as well. The cache will not be kept updated.
        force_scraping: :class:`bool`
            Whether to scrape the member sidebar regardless of permissions.
        delay: :class:`float`
            The time in seconds to wait between requests.
            This only applies when scraping from the member sidebar.

        Raises
        -------
        ClientException
            Fetching members failed.
        InvalidData
            Did not receive a response from the gateway.

        Returns
        --------
        List[:class:`Member`]
            The members that belong to this guild (offline members may not be included).
        """
        state = self._state
        if state.is_guild_evicted(self):
            return []

        members = await state.scrape_guild(self, cache=cache, force_scraping=force_scraping, delay=delay, channels=channels)
        return members

    async def query_members(
        self,
        query: Optional[str] = None,
        *,
        limit: int = 5,
        user_ids: Optional[List[int]] = None,
        presences: bool = True,
        cache: bool = True,
        subscribe: bool = False,
    ) -> List[Member]:
        """|coro|

        Request members of this guild whose username or nickname starts with the given query.
        This is a websocket operation.

        .. note::
            This is preferrable to using :meth:`fetch_member` as the client uses
            it quite often, and you can also request presence.

        .. versionadded:: 1.3

        .. versionchanged:: 2.0
            The function now raises a :exc:`TypeError` instead of ValueError.

        Parameters
        -----------
        query: Optional[:class:`str`]
            The string that the username or nickname should start with.
        limit: :class:`int`
            The maximum number of members to send back. This must be
            a number between 5 and 100.
        presences: :class:`bool`
            Whether to request for presences to be provided.
            This defaults to ``True``.

            .. versionadded:: 1.6
        cache: :class:`bool`
            Whether to cache the members internally. This makes operations
            such as :meth:`get_member` work for those that matched.
            The cache will not be kept updated unless ``subscribe`` is set to ``True``.
        user_ids: Optional[List[:class:`int`]]
            List of user IDs to search for. If the user ID is not in the guild then it won't be returned.

            .. versionadded:: 1.4
        subscribe: :class:`bool`
            Whether to subscribe to the resulting members. This will keep their member info and presence updated.
            This requires another request, and defaults to ``False``.

            See also :meth:`subscribe_to`.

            .. versionadded:: 2.0

        Raises
        -------
        asyncio.TimeoutError
            The query timed out waiting for the members.
        TypeError
            Invalid parameters were passed to the function.

        Returns
        --------
        List[:class:`Member`]
            The list of members that have matched the query.
        """
        if not query and not user_ids:
            raise TypeError('Must pass either query or user_ids')

        if user_ids and query:
            raise TypeError('Cannot pass both query and user_ids')

        limit = min(100, limit or 5)
        members = await self._state.query_members(
            self, query=query, limit=limit, user_ids=user_ids, presences=presences, cache=cache  # type: ignore # The two types are compatible
        )
        if subscribe:
            await self._state.subscriptions.subscribe_to_members(self, *members)
        return members

    async def query_recent_members(
        self,
        query: Optional[str] = None,
        *,
        limit: int = 1000,
        cache: bool = True,
    ) -> List[Member]:
        """|coro|

        Request the most recent 10,000 joined members of this guild.
        This is a websocket operation.

        .. note::

            This operation does not return presences.

        .. versionadded:: 2.1

        Parameters
        -----------
        query: Optional[:class:`str`]
            The string that the username or nickname should start with, if any.
        limit: :class:`int`
            The maximum number of members to send back. This must be
            a number between 1 and 10,000.
        cache: :class:`bool`
            Whether to cache the members internally. This makes operations
            such as :meth:`get_member` work for those that matched.
            The cache will not be kept updated.

        Raises
        -------
        asyncio.TimeoutError
            The query timed out waiting for the members.
        TypeError
            Invalid parameters were passed to the function.

        Returns
        --------
        List[:class:`Member`]
            The list of members that have matched the query.
        """
        limit = min(10000, limit or 1)
        return await self._state.search_recent_members(self, query or '', limit, cache)

    async def change_voice_state(
        self,
        *,
        channel: Optional[Snowflake],
        self_mute: bool = False,
        self_deaf: bool = False,
        self_video: bool = False,
    ) -> None:
        """|coro|

        Changes client's voice state in the guild.

        .. versionadded:: 1.4

        .. versionchanged:: 2.1

            Removed the ``preferred_region`` parameter.

        Parameters
        -----------
        channel: Optional[:class:`abc.Snowflake`]
            Channel the client wants to join. Use ``None`` to disconnect.
        self_mute: :class:`bool`
            Indicates if the client should be self-muted.
        self_deaf: :class:`bool`
            Indicates if the client should be self-deafened.
        self_video: :class:`bool`
            Indicates if the client is using video. Do not use.
        """
        state = self._state
        ws = state.ws
        channel_id = channel.id if channel else None

        await ws.voice_state(self.id, channel_id, self_mute, self_deaf, self_video)

    async def subscribe(
        self, *, typing: bool = MISSING, activities: bool = MISSING, threads: bool = MISSING, member_updates: bool = MISSING
    ) -> None:
        """|coro|

        Subscribes to a guild.

        This is required to receive most events and have a populated thread cache for large guilds.

        .. note::

            This is done automatically by default, so you do not need
            to perform this operation unless you passed ``guild_subscriptions=False``
            to your :class:`Client`. This is not recommended for most use cases.

        .. versionadded:: 2.1

        Parameters
        -----------
        typing: :class:`bool`
            Whether to receive typing events (i.e. :func:`discord.on_typing`).

            .. note::

                This is required to subscribe to large guilds (over 75,000 members).
        activities: :class:`bool`
            Currently unknown.
        threads: :class:`bool`
            Whether to populate the thread cache and receive thread events.
        member_updates: :class:`bool`
            Whether to receive member update events
            (i.e. :func:`discord.on_member_join`, :func:`discord.on_member_update`, and :func:`discord.on_member_remove`).

        Raises
        -------
        TypeError
            Attempted to subscribe to a guild without subscribing to typing events.
        """
        await self._state.subscribe_guild(
            self, typing=typing, activities=activities, threads=threads, member_updates=member_updates
        )

    async def subscribe_to(
        self, *, members: Collection[Snowflake] = MISSING, threads: Collection[Snowflake] = MISSING
    ) -> None:
        """|coro|

        Subscribes to specific members and thread member lists in the guild.

        Subscribing to members ensures their member and presence information is kept up to date,
        ensuring :func:`on_member_update`, :func:`on_user_update`, and :func:`on_presence_update` events are dispatched.

        .. versionadded:: 2.1

        Parameters
        -----------
        members: List[:class:`~abc.Snowflake`]
            A collection of members to subscribe to.
        threads: List[:class:`~abc.Snowflake`]
            A collection of threads to subscribe to.
            If these threads are cached, they will have their :attr:`~Thread.members` cache populated.

        Raises
        -------
        ValueError
            The guild is not subscribed to.
            The subscription payload is too large.
        """
        subscriptions = self._state.subscriptions
        if members:
            await subscriptions.subscribe_to_members(self, *members)
        if threads:
            await subscriptions.subscribe_to_threads(self, *threads)

    async def unsubscribe_from(
        self, *, members: Collection[Snowflake] = MISSING, threads: Collection[Snowflake] = MISSING
    ) -> None:
        """|coro|

        Unsubscribes from specific members and thread member lists in the guild.
        Any unknown members or threads are ignored.

        .. versionadded:: 2.1

        Parameters
        -----------
        members: List[:class:`~abc.Snowflake`]
            A collection of members to unsubscribe from.
        threads: List[:class:`~abc.Snowflake`]
            A collection of threads to unsubscribe from.

        Raises
        -------
        ValueError
            The guild is not subscribed to.
        """
        subscriptions = self._state.subscriptions
        if members:
            await subscriptions.unsubscribe_from_members(self, *members)
        if threads:
            await subscriptions.unsubscribe_from_threads(self, *threads)

    async def automod_rules(self) -> List[AutoModRule]:
        """|coro|

        Fetches all automod rules from the guild.

        You must have :attr:`Permissions.manage_guild` to do this.

        .. versionadded:: 2.0

        Raises
        -------
        Forbidden
            You do not have permission to view the automod rule.
        NotFound
            There are no automod rules within this guild.

        Returns
        --------
        List[:class:`AutoModRule`]
            The automod rules that were fetched.
        """
        data = await self._state.http.get_auto_moderation_rules(self.id)
        return [AutoModRule(data=d, guild=self, state=self._state) for d in data]

    async def fetch_automod_rule(self, automod_rule_id: int, /) -> AutoModRule:
        """|coro|

        Fetches an active automod rule from the guild.

        You must have :attr:`Permissions.manage_guild` to do this.

        .. versionadded:: 2.0

        Parameters
        -----------
        automod_rule_id: :class:`int`
            The ID of the automod rule to fetch.

        Raises
        -------
        Forbidden
            You do not have permission to view the automod rule.
        NotFound
            The automod rule does not exist within this guild.

        Returns
        --------
        :class:`AutoModRule`
            The automod rule that was fetched.
        """
        data = await self._state.http.get_auto_moderation_rule(self.id, automod_rule_id)
        return AutoModRule(data=data, guild=self, state=self._state)

    async def create_automod_rule(
        self,
        *,
        name: str,
        event_type: AutoModRuleEventType,
        trigger: AutoModTrigger,
        actions: List[AutoModRuleAction],
        enabled: bool = False,
        exempt_roles: Sequence[Snowflake] = MISSING,
        exempt_channels: Sequence[Snowflake] = MISSING,
        reason: str = MISSING,
    ) -> AutoModRule:
        """|coro|

        Create an automod rule.

        You must have :attr:`Permissions.manage_guild` to do this.

        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`str`
            The name of the automod rule.
        event_type: :class:`AutoModRuleEventType`
            The type of event that the automod rule will trigger on.
        trigger: :class:`AutoModTrigger`
            The trigger that will trigger the automod rule.
        actions: List[:class:`AutoModRuleAction`]
            The actions that will be taken when the automod rule is triggered.
        enabled: :class:`bool`
            Whether the automod rule is enabled.
            Defaults to ``False``.
        exempt_roles: Sequence[:class:`abc.Snowflake`]
            A list of roles that will be exempt from the automod rule.
        exempt_channels: Sequence[:class:`abc.Snowflake`]
            A list of channels that will be exempt from the automod rule.
        reason: :class:`str`
            The reason for creating this automod rule. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have permissions to create an automod rule.
        HTTPException
            Creating the automod rule failed.

        Returns
        --------
        :class:`AutoModRule`
            The automod rule that was created.
        """
        data = await self._state.http.create_auto_moderation_rule(
            self.id,
            name=name,
            event_type=event_type.value,
            trigger_type=trigger.type.value,
            trigger_metadata=trigger.to_metadata_dict() or None,
            actions=[a.to_dict() for a in actions],
            enabled=enabled,
            exempt_roles=[str(r.id) for r in exempt_roles] if exempt_roles else None,
            exempt_channels=[str(c.id) for c in exempt_channels] if exempt_channels else None,
            reason=reason,
        )

        return AutoModRule(data=data, guild=self, state=self._state)

    async def admin_community_eligibility(self) -> bool:
        """|coro|

        Checks if the user is eligible to join the Discord Admin Community through the guild.

        .. versionadded:: 2.1

        Raises
        -------
        Forbidden
            You do not have permissions to join through the guild.
        HTTPException
            Checking eligibility failed.

        Returns
        --------
        :class:`bool`
            Whether the user is eligible to join the Discord Admin Community through the guild.
        """
        data = await self._state.http.get_admin_server_eligibility(self.id)
        return data['eligible_for_admin_server']

    async def join_admin_community(self) -> Guild:
        """|coro|

        Joins the Discord Admin Community through the guild.
        You should check your eligibility with :meth:`admin_community_eligibility` before calling this.

        .. versionadded:: 2.1

        Raises
        -------
        Forbidden
            You do not have permissions to join through the guild.
        HTTPException
            Joining failed.

        Returns
        --------
        :class:`Guild`
            The Discord Admin Community guild.
        """
        data = await self._state.http.join_admin_server(self.id)
        return Guild(state=self._state, data=data)

    async def migrate_command_scope(self) -> List[int]:
        """|coro|

        Migrates the guild's bot integrations to the applications.commands scope.

        .. versionadded:: 2.1

        Raises
        -------
        Forbidden
            You do not have permissions to migrate the guild's bots.
        HTTPException
            Migrating failed.

        Returns
        --------
        List[:class:`int`]
            The integration IDs that have newly-added application commands.
        """
        data = await self._state.http.migrate_command_scope(self.id)
        return list(map(int, data['integration_ids_with_app_commands']))

    async def directory_broadcast_eligibility(
        self, scheduled_event: Optional[Snowflake] = None, /
    ) -> DirectoryBroadcastEligibility:
        """|coro|

        Checks if scheduled events can be broadcasted to the directories the guild is in.

        .. versionadded:: 2.1

        Parameters
        -----------
        scheduled_event: Optional[:class:`ScheduledEvent`]
            The scheduled event to check eligibility for.

        Raises
        -------
        HTTPException
            Checking eligibility failed.

        Returns
        --------
        tuple[:class:`bool`, :class:`bool`]
            Whether the guild is eligible to broadcast scheduled events to directories
            and whether the given scheduled event has been broadcasted, if applicable.
            This is also accessible as a namedtuple with ``can_broadcast`` and ``has_broadcast`` fields.
        """
        data = await self._state.http.get_directory_broadcast_info(
            self.id, 1, scheduled_event.id if scheduled_event else None
        )
        return DirectoryBroadcastEligibility(data['can_broadcast'], data.get('has_broadcast', False))

    @property
    def invites_paused_until(self) -> Optional[datetime]:
        """Optional[:class:`datetime.datetime`]: If invites are paused, returns when
        invites will get enabled in UTC, otherwise returns None.

        .. versionadded:: 2.1
        """
        if not self._incidents_data:
            return None

        return utils.parse_time(self._incidents_data.get('invites_disabled_until'))

    @property
    def dms_paused_until(self) -> Optional[datetime]:
        """Optional[:class:`datetime.datetime`]: If DMs are paused, returns when DMs
        will get enabled in UTC, otherwise returns None.

        .. versionadded:: 2.1
        """
        if not self._incidents_data:
            return None

        return utils.parse_time(self._incidents_data.get('dms_disabled_until'))

    @property
    def dm_spam_detected_at(self) -> Optional[datetime]:
        """:class:`datetime.datetime`: Returns the time when DM spam was detected in the guild.

        .. versionadded:: 2.1
        """
        if not self._incidents_data:
            return None

        return utils.parse_time(self._incidents_data.get('dm_spam_detected_at'))

    @property
    def raid_detected_at(self) -> Optional[datetime]:
        """Optional[:class:`datetime.datetime`]: Returns the time when a raid was detected in the guild.

        .. versionadded:: 2.1
        """
        if not self._incidents_data:
            return None

        return utils.parse_time(self._incidents_data.get('raid_detected_at'))

    def invites_paused(self) -> bool:
        """:class:`bool`: Whether invites are paused in the guild.

        .. versionadded:: 2.1
        """
        if not self.invites_paused_until:
            return 'INVITES_DISABLED' in self.features

        return self.invites_paused_until > utils.utcnow()

    def dms_paused(self) -> bool:
        """:class:`bool`: Whether DMs are paused in the guild.

        .. versionadded:: 2.1
        """
        if not self.dms_paused_until:
            return False

        return self.dms_paused_until > utils.utcnow()

    def is_dm_spam_detected(self) -> bool:
        """:class:`bool`: Whether DM spam was detected in the guild.

        .. versionadded:: 2.1
        """
        if not self.dm_spam_detected_at:
            return False

        return self.dm_spam_detected_at > utils.utcnow()

    def is_raid_detected(self) -> bool:
        """:class:`bool`: Whether a raid was detected in the guild.

        .. versionadded:: 2.1
        """
        if not self.raid_detected_at:
            return False

        return self.raid_detected_at > utils.utcnow()
