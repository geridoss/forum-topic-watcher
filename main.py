"""A Discord bot that keeps a live list of the five most recently active forum threads."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone

import discord
from aiohttp import web
from dotenv import load_dotenv
from discord.ext import commands, tasks

load_dotenv()


def parse_ids(value: str) -> set[int]:
    return {int(part.strip()) for part in value.split(",") if part.strip()}


TOKEN = os.environ["DISCORD_TOKEN"]
FORUM_CHANNEL_IDS = parse_ids(os.environ["FORUM_CHANNEL_IDS"])
POST_CHANNEL_ID = int(os.environ["POST_CHANNEL_ID"])
RUN_ONCE = os.getenv("BOT_RUN_ONCE") == "1"
exit_code = 0
# Invisible separator keeps the bot's tracking marker out of the visible post.
POST_MARKER = "\u2063"

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.default()


class ForumWatcherBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=intents)
        self.health_runner: web.AppRunner | None = None

    async def setup_hook(self) -> None:
        # GitHub's one-shot run exits after updating and does not need an HTTP listener.
        if RUN_ONCE:
            return

        app = web.Application()

        async def health(_: web.Request) -> web.Response:
            return web.Response(text="ok", content_type="text/plain")

        app.router.add_get("/health", health)
        self.health_runner = web.AppRunner(app, access_log=None)
        await self.health_runner.setup()
        site = web.TCPSite(
            self.health_runner,
            host="0.0.0.0",
            port=int(os.getenv("PORT", "10000")),
        )
        await site.start()
        logging.info("Health endpoint elindult a /health útvonalon.")

    async def close(self) -> None:
        if self.health_runner is not None:
            await self.health_runner.cleanup()
            self.health_runner = None
        await super().close()


bot = ForumWatcherBot()


def activity_time(thread: discord.Thread) -> datetime:
    # A Discord snowflake's timestamp corresponds to when its message was created.
    if thread.last_message_id:
        return discord.utils.snowflake_time(thread.last_message_id)
    return thread.created_at


async def make_embed(guild: discord.Guild) -> discord.Embed:
    active_threads = await guild.active_threads()
    threads = [
        thread
        for thread in active_threads
        if thread.parent_id in FORUM_CHANNEL_IDS and not thread.archived
    ]
    threads.sort(key=activity_time, reverse=True)

    embed = discord.Embed(
        title="Legutóbb aktív fórumtopikok",
        description="Az öt topik, amelyhez legutóbb hozzászóltak.",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc),
    )
    if not threads:
        embed.description = "Jelenleg nincs aktív topik a figyelt fórumcsatornákban."
    else:
        for index, thread in enumerate(threads[:5], start=1):
            when = int(activity_time(thread).timestamp())
            embed.add_field(
                name=f"{index}. {thread.name}",
                value=f"<#{thread.id}> · <t:{when}:R>",
                inline=False,
            )
    embed.set_footer(text="Automatikusan frissül")
    return embed


async def update_post() -> None:
    channel = bot.get_channel(POST_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(POST_CHANNEL_ID)
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        raise TypeError("A POST_CHANNEL_ID szöveges csatornára mutasson.")
    guild = channel.guild
    embed = await make_embed(guild)

    async for message in channel.history(limit=100):
        if message.author.id == bot.user.id and POST_MARKER in message.content:
            await message.edit(content=POST_MARKER, embed=embed)
            return
    await channel.send(content=POST_MARKER, embed=embed)


@tasks.loop(minutes=1)
async def refresh_topics() -> None:
    try:
        await update_post()
    except Exception:
        logging.exception("Nem sikerült frissíteni az aktív topikok listáját")


@refresh_topics.before_loop
async def before_refresh() -> None:
    await bot.wait_until_ready()


@bot.event
async def on_ready() -> None:
    global exit_code
    logging.info("Bejelentkezve: %s", bot.user)
    if RUN_ONCE:
        try:
            await update_post()
            logging.info("A topiklista frissítése sikerült.")
        except Exception:
            exit_code = 1
            logging.exception("Nem sikerült frissíteni az aktív topikok listáját")
        finally:
            await bot.close()
        return
    if not refresh_topics.is_running():
        refresh_topics.start()


if not FORUM_CHANNEL_IDS:
    raise SystemExit("A FORUM_CHANNEL_IDS mezőben legalább egy fórumcsatorna-ID kell.")

bot.run(TOKEN)
if exit_code:
    sys.exit(exit_code)
