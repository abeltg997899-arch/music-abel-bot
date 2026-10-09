
import os
import asyncio
import discord
import wavelink
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "2333"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    print(f"Music Abel connected as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as error:
        print(f"Slash command sync error: {error}")


async def connect_lavalink():
    if not all([TOKEN, LAVALINK_HOST, LAVALINK_PASSWORD]):
        raise RuntimeError(
            "Missing DISCORD_TOKEN, LAVALINK_HOST, or LAVALINK_PASSWORD."
        )

    node = wavelink.Node(
        uri=f"http://{LAVALINK_HOST}:{LAVALINK_PORT}",
        password=LAVALINK_PASSWORD,
    )
    await wavelink.Pool.connect(
        client=bot,
        nodes=[node],
    )
    print("Connected to Lavalink.")


@bot.event
async def setup_hook():
    await connect_lavalink()


@bot.tree.command(name="join", description="Join your voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message(
            "Join a voice channel first.", ephemeral=True
        )
        return

    try:
        await interaction.user.voice.channel.connect(cls=wavelink.Player)
        await interaction.response.send_message("Joined your voice channel.")
    except Exception as error:
        await interaction.response.send_message(
            f"Could not join: {error}", ephemeral=True
        )


@bot.tree.command(name="play", description="Search for and play a song")
@app_commands.describe(query="Song name or URL")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("Join a voice channel first.")
        return

    player = interaction.guild.voice_client

    if not player:
        player = await interaction.user.voice.channel.connect(cls=wavelink.Player)

    try:
        tracks = await wavelink.Playable.search(query)

        if not tracks:
            await interaction.followup.send("No tracks found.")
            return

        track = tracks[0]
        await player.play(track)
        await interaction.followup.send(f"▶️ Now playing: **{track.title}**")

    except Exception as error:
        await interaction.followup.send(f"Playback error: {error}")


@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        await interaction.response.send_message("I'm not in a voice channel.")
        return
    await player.pause(True)
    await interaction.response.send_message("⏸️ Paused.")


@bot.tree.command(name="resume", description="Resume playback")
async def resume(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        await interaction.response.send_message("I'm not in a voice channel.")
        return
    await player.pause(False)
    await interaction.response.send_message("▶️ Resumed.")


@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        await interaction.response.send_message("I'm not in a voice channel.")
        return
    await player.skip(force=True)
    await interaction.response.send_message("⏭️ Skipped.")


@bot.tree.command(name="stop", description="Stop playback")
async def stop(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        await interaction.response.send_message("I'm not in a voice channel.")
        return
    await player.stop()
    await interaction.response.send_message("⏹️ Stopped.")


@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        await interaction.response.send_message("I'm not in a voice channel.")
        return
    await player.disconnect()
    await interaction.response.send_message("👋 Left the voice channel.")


@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print("Lavalink node is ready.")


if __name__ == "__main__":
    bot.run(TOKEN)
