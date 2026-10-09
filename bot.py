
import os
import discord
import wavelink
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = os.getenv("LAVALINK_PORT", "2333")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")


class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        if not LAVALINK_HOST or not LAVALINK_PASSWORD:
            raise RuntimeError("Missing Lavalink environment variables.")

        node = wavelink.Node(
            uri=f"http://{LAVALINK_HOST}:{LAVALINK_PORT}",
            password=LAVALINK_PASSWORD,
        )

        await wavelink.Pool.connect(client=self, nodes=[node])
        print("Connected to Lavalink.")

        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands.")
        except Exception as error:
            print(f"Slash command sync error: {error}")

    async def on_ready(self):
        print(f"Music Abel connected as {self.user}")

    async def on_wavelink_node_ready(
        self, payload: wavelink.NodeReadyEventPayload
    ):
        print("Lavalink node is ready.")


bot = MusicBot()


async def get_player(interaction: discord.Interaction):
    if interaction.guild is None:
        raise ValueError("Use this command inside a server.")

    member = interaction.user
    if not isinstance(member, discord.Member):
        raise ValueError("Could not identify the server member.")

    if member.voice is None or member.voice.channel is None:
        raise ValueError("Join a voice channel first.")

    player = interaction.guild.voice_client

    if player is None:
        player = await member.voice.channel.connect(cls=wavelink.Player)
    elif player.channel != member.voice.channel:
        raise ValueError("I'm already connected to another voice channel.")

    return player


@bot.tree.command(name="join", description="Join your voice channel")
@app_commands.guild_only()
async def join(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await get_player(interaction)
        await interaction.followup.send("Joined your voice channel.", ephemeral=True)
    except Exception as error:
        await interaction.followup.send(f"Could not join: {error}", ephemeral=True)


@bot.tree.command(name="play", description="Search for and play a song")
@app_commands.describe(query="Song name or URL")
@app_commands.guild_only()
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    try:
        player = await get_player(interaction)

        if query.startswith(("http://", "https://")):
            search_query = query
        else:
            search_query = f"scsearch:{query}"

        tracks = await wavelink.Playable.search(search_query)
        if not tracks:
            await interaction.followup.send("No tracks found on SoundCloud.")
            return

        track = tracks[0]
        await player.play(track)
        await interaction.followup.send(f"Now playing: **{track.title}**")
    except Exception as error:
        await interaction.followup.send(f"Playback error: {error}")


@bot.tree.command(name="pause", description="Pause the current song")
@app_commands.guild_only()
async def pause(interaction: discord.Interaction):
    player = interaction.guild.voice_client if interaction.guild else None
    if player is None:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
        return
    try:
        await player.pause(True)
        await interaction.response.send_message("Paused.")
    except Exception as error:
        await interaction.response.send_message(f"Could not pause: {error}", ephemeral=True)


@bot.tree.command(name="resume", description="Resume playback")
@app_commands.guild_only()
async def resume(interaction: discord.Interaction):
    player = interaction.guild.voice_client if interaction.guild else None
    if player is None:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
        return
    try:
        await player.pause(False)
        await interaction.response.send_message("Resumed.")
    except Exception as error:
        await interaction.response.send_message(f"Could not resume: {error}", ephemeral=True)


@bot.tree.command(name="skip", description="Skip the current song")
@app_commands.guild_only()
async def skip(interaction: discord.Interaction):
    player = interaction.guild.voice_client if interaction.guild else None
    if player is None:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
        return
    try:
        await player.skip(force=True)
        await interaction.response.send_message("Skipped.")
    except Exception as error:
        await interaction.response.send_message(f"Could not skip: {error}", ephemeral=True)


@bot.tree.command(name="stop", description="Stop playback")
@app_commands.guild_only()
async def stop(interaction: discord.Interaction):
    player = interaction.guild.voice_client if interaction.guild else None
    if player is None:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
        return
    try:
        await player.stop()
        await interaction.response.send_message("Playback stopped.")
    except Exception as error:
        await interaction.response.send_message(f"Could not stop: {error}", ephemeral=True)


@bot.tree.command(name="leave", description="Leave the voice channel")
@app_commands.guild_only()
async def leave(interaction: discord.Interaction):
    player = interaction.guild.voice_client if interaction.guild else None
    if player is None:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
        return
    try:
        await player.disconnect()
        await interaction.response.send_message("Left the voice channel.")
    except Exception as error:
        await interaction.response.send_message(f"Could not leave: {error}", ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing from Railway variables.")
    bot.run(TOKEN)