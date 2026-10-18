"""Keep a live list of recent activity in forum threads and text channels."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

import discord
from aiohttp import web
from dotenv import load_dotenv
from discord.ext import commands, tasks

load_dotenv()


def parse_ids(value: str) -> set[int]:
    return {int(part.strip()) for part in value.split(",") if part.strip()}


TOKEN = os.environ["DISCORD_TOKEN"]
FORUM_CHANNEL_IDS = parse_ids(os.getenv("FORUM_CHANNEL_IDS", ""))
TEXT_CHANNEL_IDS = parse_ids(os.getenv("TEXT_CHANNEL_IDS", ""))
POST_CHANNEL_ID = int(os.environ["POST_CHANNEL_ID"])
TOPIC_LIMIT = int(os.getenv("TOPIC_LIMIT") or "5")
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


@dataclass(frozen=True)
class Activity:
    timestamp: datetime
    name: str
    channel_mention: str


async def make_embed(guild: discord.Guild) -> discord.Embed:
    active_threads = await guild.active_threads()
    activities = [
        Activity(
            timestamp=activity_time(thread),
            name=thread.name,
            channel_mention=f"<#{thread.id}>",
        )
        for thread in active_threads
        if thread.parent_id in FORUM_CHANNEL_IDS and not thread.archived
    ]

    for channel_id in TEXT_CHANNEL_IDS:
        try:
            channel = bot.get_channel(channel_id)
            if channel is None:
                channel = await bot.fetch_channel(channel_id)
            if not isinstance(channel, discord.TextChannel) or channel.guild.id != guild.id:
                logging.warning(
                    "A TEXT_CHANNEL_IDS értéke nem a szerver szöveges csatornája: %s",
                    channel_id,
                )
                continue

            latest_message = None
            async for message in channel.history(limit=10):
                # Avoid treating this bot's own list post as user activity if the
                # destination channel is also configured for monitoring.
                if bot.user is not None and message.author.id == bot.user.id:
                    continue
                latest_message = message
                break

            if latest_message is not None:
                activities.append(
                    Activity(
                        timestamp=latest_message.created_at,
                        name=f"#{channel.name}",
                        channel_mention=channel.mention,
                    )
                )
        except discord.Forbidden:
            logging.warning(
                "Nincs hozzáférés a figyelt szöveges csatornához: %s", channel_id
            )
        except discord.HTTPException:
            logging.exception(
                "Nem sikerült lekérni a figyelt szöveges csatornát: %s", channel_id
            )

    activities.sort(key=lambda activity: activity.timestamp, reverse=True)

    embed = discord.Embed(
        title="Legutóbb aktív fórumtopikok és szöveges csatornák",
        description=f"A legutóbbi {TOPIC_LIMIT} aktivitás a figyelt helyekről.",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc),
    )
    if not activities:
        embed.description = "Jelenleg nincs aktivitás a figyelt fórumtopikokban és szöveges csatornákban."
    else:
        for index, activity in enumerate(activities[:TOPIC_LIMIT], start=1):
            when = int(activity.timestamp.timestamp())
            embed.add_field(
                name=f"{index}. {activity.name}",
                value=f"{activity.channel_mention} · <t:{when}:R>",
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


if TOPIC_LIMIT < 1:
    raise SystemExit("A TOPIC_LIMIT értéke legalább 1 legyen.")
if TOPIC_LIMIT > 25:
    raise SystemExit("A TOPIC_LIMIT legfeljebb 25 lehet a Discord beágyazáskorlátja miatt.")
if not FORUM_CHANNEL_IDS and not TEXT_CHANNEL_IDS:
    raise SystemExit("Legalább egy fórum- vagy szöveges csatorna-ID-t meg kell adni.")

bot.run(TOKEN)
if exit_code:
    sys.exit(exit_code)
