from __future__ import annotations

import asyncio

from typing import List, Union, Callable, TYPE_CHECKING

from discord import Emoji

if TYPE_CHECKING:
    from discord import Reaction, User
    from ext.context import Context


class PaginationCallback:
    def __init__(self, __class: Paginate, reaction: Reaction = None, user: User = None):
        if not isinstance(__class, Paginate):
            raise TypeError("__class must derives from Paginate instance.")
        self.base_class = __class
        self.reactions = __class.reactions
        self.message = __class.message
        self.bot = asyncio.create_task(__class.context.bot.get_context(self.message))
        self.reaction = reaction
        self.user = user
        self.destination = __class.destination
        self.target = __class.target


class Paginate:
    def __init__(self, message=None,
                 reactions: List[Union[str, Emoji]] = None,
                 check: Callable = None, timeout: int = None,
                 user: User = None, pages=None, start_from_page: int = 0):
        self.reactions = reactions or ["⬅️", "➡️"]
        self.message = message
        self.page = start_from_page
        self.pages = pages
        self.check = check
        self.timeout = timeout
        self.__callback = PaginationCallback
        self.target = user or self.context.author
        self.destination = message.channel if message is not None else self.context.channel
        if self.message is None and self.pages:
            asyncio.create_task(self._ensure_message())

    async def _ensure_message(self):
        self.message = await self.destination.send(embed=self.pages[self.page])
        for reaction in self.reactions:
            await self.add_item(reaction,
                                check=lambda callback:
                                str(callback.reaction) in self.reactions
                                and callback.user == self.target
                                )

    async def add_item(self, reaction: Union[str, Emoji],
                       check: Callable = None,
                       __callback: Callable = None):
        await self.message.add_reaction(reaction)
        asyncio.create_task(self.listen(reaction, check, __callback))

    @classmethod
    def from_context(cls, context: Context):
        cls.context = context

    async def callback(self, r, u):  # noqa
        if str(r.emoji) == "⬅️":
            if self.page > 0:
                self.page -= 1
                await self.message.edit(embed=self.pages[self.page])
        elif str(r.emoji) == "➡️":
            if self.page < len(self.pages) - 1:
                self.page += 1
                await self.message.edit(embed=self.pages[self.page])

    async def listen(self, reaction: Union[str, Emoji, int],
                     check: Callable = None,
                     callback: Callable = None):
        r, u = await self.context.bot.wait_for("reaction_add",
                                               check=lambda re, us: str(re.emoji) == str(reaction),
                                               timeout=self.timeout
                                               )
        if check is None:
            if callback is not None:
                callback(r, u)
            else:
                await self.callback(r, u)
        elif check(self.__callback(self, r, u)):  # pass the PaginationCallback to `check` parameter
            if callback is not None:
                callback(r, u)
            else:
                await self.callback(r, u)

        await self.listen(reaction, check, callback)
