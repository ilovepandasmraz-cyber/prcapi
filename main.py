import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
from datetime import datetime, timezone, timedelta
import typing
import atexit
import copy
from discord.ext import commands, tasks

# ----------------

session: aiohttp.ClientSession | None = None

load_dotenv()

# -------- Bot Setup --------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

GUILD_ID = "1299000909363155024"  # Replace with your Discord Server ID
API_KEY = os.getenv("API_KEY")
API_BASE = "https://api.policeroleplay.community/v1/server"
ROBLOX_USER_API = "https://users.roblox.com/v1/users"
PRC_HEADERS = {"server-key": API_KEY, "Accept": "application/json"}
server_name = "test"
staff_role_id = "1316076193459474525" # replace with your staff role ID
join_link = "https://policeroleplay.community/join?code=&placeId=2534724415" 
# put your erlc join code in code=(your join code) so it looks something like this https://policeroleplay.community/join?code=SWATxRP&placeId=2534724415


erlc_group = app_commands.Group(name="erlc", description="ERLC related commands")
discord_group = app_commands.Group(name="discord", description="Discord-related commands")

bot.tree.add_command(erlc_group)
bot.tree.add_command(discord_group)

# Session Helper
async def get_session():
    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()
    return session

# Error Messages
# (get_error_message function unchanged from your original)

# is_staff decorator

def is_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
            member = await interaction.guild.fetch_member(interaction.user.id)
        return any(role.id == int(staff_role_id) for role in member.roles)
    return app_commands.check(predicate)

# Utility: Footer Helper

def apply_footer(embed, guild):
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"{server_name}")
    return embed

# === HANDLE ERROR CODES ===
def get_error_message(http_status: int, api_code: str = None) -> str:
    messages = {
        0:    "**0 – Unknown Error**: An unknown error occurred. Please contact support if this continues.",
        100:  "**100 – Continue**: The request headers were received, continue with the request body.",
        101:  "**101 – Switching Protocols**: The server is switching protocols.",
        200:  "**200 – OK**: The request completed successfully.",
        201:  "**201 – Created**: The request succeeded and a new resource was created.",
        204:  "**204 – No Content**: Success, but no content returned.",
        400:  "**400 – Bad Request**: The request was malformed or invalid.",
        401:  "**401 – Unauthorized**: Missing or invalid authentication.",
        403:  "**403 – Forbidden**: You do not have permission to access this resource.",
        404:  "**404 – Not Found**: The requested resource does not exist.",
        405:  "**405 – Method Not Allowed**: That method is not allowed on this endpoint.",
        408:  "**408 – Request Timeout**: The server timed out waiting for the request.",
        409:  "**409 – Conflict**: The request could not be completed due to a conflict.",
        410:  "**410 – Gone**: The resource has been permanently removed.",
        415:  "**415 – Unsupported Media Type**: The media type is not supported.",
        418:  "**418 – I'm a teapot**: The server refuses to brew coffee in a teapot.",
        422:  "**422 – No Players**: No players are currently in the private server.",
        429:  "**429 – Too Many Requests**: You are being rate-limited. Slow down.",
        500:  "**500 – Internal Server Error**: An internal server error occurred (possibly with Roblox).",
        501:  "**501 – Not Implemented**: The server doesn't recognize this method.",
        502:  "**502 – Bad Gateway**: Invalid response from an upstream server.",
        503:  "**503 – Service Unavailable**: The server is overloaded or under maintenance.",
        504:  "**504 – Gateway Timeout**: The upstream server did not respond in time.",
        1001: "**1001 – Communication Error**: Failed to communicate with Roblox or the in-game server.",
        1002: "**1002 – System Error**: A backend error occurred. Try again later.",
        2000: "**2000 – Missing Server Key**: No server-key provided.",
        2001: "**2001 – Bad Server Key Format**: Server-key format is invalid.",
        2002: "**2002 – Invalid Server Key**: The server-key is incorrect or expired.",
        2003: "**2003 – Invalid Global API Key**: The global API key is invalid.",
        2004: "**2004 – Banned Server Key**: Your server-key is banned from using the API.",
        3001: "**3001 – Missing Command**: No command was specified in the request body.",
        3002: "**3002 – Server Offline**: The server is currently offline or empty.",
        4001: "**4001 – Rate Limited**: You are being rate limited. Please wait and try again.",
        4002: "**4002 – Command Restricted**: The command you’re trying to run is restricted.",
        4003: "**4003 – Prohibited Message**: The message you’re trying to send is not allowed.",
        9998: "**9998 – Resource Restricted**: You are trying to access a restricted resource.",
        9999: "**9999 – Module Outdated**: The in-game module is outdated. Please restart the server.",
    }

    base_message = messages.get(http_status, f"**{http_status} – Unknown Error**: An unexpected error occurred.")
    if api_code:
        base_message += f"\nAPI Code: `{api_code}`"
    return base_message

# -------- Bot Commands --------

@tree.command(name="ping", description="Check bot's latency and uptime")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)  # in ms
    now = datetime.now(timezone.utc)
    uptime_duration = now - bot.start_time
    uptime_str = str(timedelta(seconds=int(uptime_duration.total_seconds())))

    embed = discord.Embed(
        title=f"{server_name}",
        description=(
            "Information about the bot status\n"
            f"> Latency: `{latency} ms`\n"
            f"> Uptime: `{uptime_str}`\n"
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        ),
        color=discord.Color.blue()
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    embed.set_footer(text=f"{server_name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="user", description="Get public info about a Roblox user by ID")
@app_commands.describe(user_id="The Roblox User ID to fetch info for")
async def roblox_user_info(interaction: discord.Interaction, user_id: str):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        # Get basic user info
        async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
            if resp.status != 200:
                await interaction.followup.send(f"Failed to fetch Roblox user. Status: {resp.status}")
                return
            user_data = await resp.json()

        # Get status
        async with session.get(f"https://users.roblox.com/v1/users/{user_id}/status") as resp2:
            status_data = await resp2.json() if resp2.status == 200 else {}

        # Avatar thumbnail (headshot) and full avatar image
        headshot_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=150&height=150&format=png"
        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png&isCircular=false"

        # Get avatar image URL from the thumbnails API
        async with session.get(avatar_url) as avatar_resp:
            avatar_json = await avatar_resp.json()
            avatar_img_url = avatar_json['data'][0]['imageUrl'] if avatar_resp.status == 200 and avatar_json['data'] else None

        # Build embed
        embed = discord.Embed(
            title="👤 Roblox User Info",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Username", value=user_data.get("name", "Unknown"), inline=True)
        embed.add_field(name="Display Name", value=user_data.get("displayName", "Unknown"), inline=True)
        embed.add_field(name="User ID", value=str(user_data.get("id", "Unknown")), inline=True)
        embed.add_field(name="Description", value=user_data.get("description", "None"), inline=False)
        embed.add_field(name="Created", value=user_data.get("created", "Unknown"), inline=False)
        embed.add_field(name="Status", value=status_data.get("status", "None"), inline=False)

        embed.set_thumbnail(url=headshot_url)
        if avatar_img_url:
            embed.set_image(url=avatar_img_url)

        await interaction.followup.send(embed=embed)

async def get_roblox_usernames(ids: list[int]) -> dict[int, str]:
    usernames = {}
    async with aiohttp.ClientSession() as session:
        for user_id in ids:
            async with session.get(f"{ROBLOX_USER_API}/{user_id}") as res:
                if res.status == 200:
                    data = await res.json()
                    usernames[user_id] = data.get("name", f"ID:{user_id}")
                else:
                    usernames[user_id] = f"ID:{user_id}"
    return usernames

class InfoView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, embed_callback):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.embed_callback = embed_callback

        self.add_item(discord.ui.Button(
            label="Join Server",
            style=discord.ButtonStyle.link,
            url=f"{join_link}"
        ))

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.blurple)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("You can't use this button.", ephemeral=True)
            return

        embed = await self.embed_callback()
        await interaction.response.edit_message(embed=embed)

async def create_server_info_embed(interaction: discord.Interaction) -> discord.Embed:
    global session
    if session is None:
        raise Exception("HTTP session not initialized")

    headers = {"server-key": API_KEY, "Accept": "*/*"}
    async with session.get(f"{API_BASE}", headers=headers) as res:
        if res.status != 200:
            raise Exception("Failed to fetch server data.")
        server = await res.json()

    async with session.get(f"{API_BASE}/players", headers=headers) as res:
        players = await res.json()

    async with session.get(f"{API_BASE}/queue", headers=headers) as res:
        queue = await res.json()

    owner_id = server["OwnerId"]
    co_owner_ids = server.get("CoOwnerIds", [])
    usernames = await get_roblox_usernames([owner_id] + co_owner_ids)

    mods = [p for p in players if p.get("Permission") == "Server Moderator"]
    admins = [p for p in players if p.get("Permission") == "Server Administrator"]
    staff = [p for p in players if p.get("Permission") != "Normal"]

    embed = discord.Embed(
        title=f"{server_name} - Server Info",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Basic Info",
        value=(
            f"> **Join Code:** [{server['JoinKey']}](https://policeroleplay.community/join/{server['JoinKey']})\n"
            f"> **Players:** {server['CurrentPlayers']}/{server['MaxPlayers']}\n"
            f"> **Queue:** {len(queue)}"
        ),
        inline=False
    )
    embed.add_field(
        name="Staff Info",
        value=(
            f"> **Moderators:** {len(mods)}\n"
            f"> **Administrators:** {len(admins)}\n"
            f"> **Staff in Server:** {len(staff)}"
        ),
        inline=False
    )
    embed.add_field(
        name=f"Server Ownership",
        value=(
            f"> **Owner:** [{usernames[owner_id]}](https://roblox.com/users/{owner_id}/profile)\n"
            f"> **Co-Owners:** {', '.join([f'[{usernames[uid]}](https://roblox.com/users/{uid}/profile)' for uid in co_owner_ids]) or 'None'}"
        ),
        inline=False
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text=f"{server_name}")

    return embed

# Add a subcommand to /erlc -> /erlc info
@erlc_group.command(name="info", description="Get ER:LC server info with live data.")
async def erlc_info(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        embed = await create_server_info_embed(interaction)
        view = InfoView(interaction, lambda: create_server_info_embed(interaction))
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        print(f"[ERROR] /info command failed: {e}")
        await interaction.followup.send("Failed to fetch server information.")



@erlc_group.command(name="players", description="See all players in the server.")
@app_commands.describe(filter="Filter players by username prefix (optional)")
async def players(interaction: discord.Interaction, filter: str = None):
    await interaction.response.defer()

    global session
    if session is None:
        await interaction.followup.send("HTTP session not ready.")
        return

    headers = {"server-key": API_KEY}
    async with session.get(f"{API_BASE}/players", headers=headers) as resp:
        if resp.status != 200:
            await interaction.followup.send(f"Failed to fetch players (status {resp.status})")
            return
        players_data = await resp.json()

    async with session.get(f"{API_BASE}/queue", headers=headers) as resp:
        if resp.status != 200:
            await interaction.followup.send(f"Failed to fetch queue (status {resp.status})")
            return
        queue_data = await resp.json()

    staff = []
    actual_players = []

    for p in players_data:
        try:
            username, id_str = p["Player"].split(":")
            player_id = int(id_str)
        except Exception:
            continue
        permission = p.get("Permission", "Normal")
        team = p.get("Team", "")

        if filter and not username.lower().startswith(filter.lower()):
            continue

        player_info = {
            "username": username,
            "id": player_id,
            "team": team,
        }

        if permission == "Normal":
            actual_players.append(player_info)
        else:
            staff.append(player_info)

    def format_players(players_list):
        if not players_list:
            return "> No players in this category."
        return ", ".join(
            f"[{p['username']} ({p['team']})](https://roblox.com/users/{p['id']}/profile)" for p in players_list
        )

    embed = discord.Embed(
        title=f"{server_name} - Players",
        color=discord.Color.blue()
    )

    embed.description = (
        f"**Server Staff ({len(staff)})**\n"
        f"{format_players(staff)}\n\n"
        f"**Online Players ({len(actual_players)})**\n"
        f"{format_players(actual_players)}\n\n"
        f"**Queue ({len(queue_data)})**\n"
        f"{'> No players in queue.' if not queue_data else ', '.join(str(qid) for qid in queue_data)}"
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text=f"{server_name}")

    await interaction.followup.send(embed=embed)

def is_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
            member = await interaction.guild.fetch_member(interaction.user.id)
        if any(role.id == staff_role_id for role in member.roles):
            return True
        raise app_commands.CheckFailure("{failed_emoji} You do not have permission to use this command.")
    return app_commands.check(predicate)

async def get_server_players():
    global session
    if session is None:
        return []
    url = f"{API_BASE}/players"
    headers = {"server-key": API_KEY}
    async with session.get(url, headers=headers) as resp:
        return await resp.json() if resp.status == 200 else []

@erlc_group.command(name="teams", description="See all players grouped by team.")
@is_staff()
@app_commands.describe(filter="Filter players by username prefix (optional)")
async def teams(interaction: discord.Interaction, filter: typing.Optional[str] = None):
    await interaction.response.defer()
    players = await get_server_players()
    teams = {}

    for plr in players:
        if ":" not in plr.get("Player", ""):
            continue
        username, userid = plr["Player"].split(":", 1)

        if filter and not username.lower().startswith(filter.lower()):
            continue

        team = plr.get("Team", "Unknown") or "Unknown"
        teams.setdefault(team, []).append({"username": username, "id": userid})

    team_order = ["Police", "Sheriff", "Fire", "DOT", "Civilian", "Jail"]
    embed_desc = ""

    for team in team_order:
        count = len(teams.get(team, []))
        embed_desc += f"**{team}** {count}\n\n"

    embed = discord.Embed(title="Server Players by Team", description=embed_desc, color=discord.Color.blue())
    embed.set_footer(text=f"{server_name}")
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    await interaction.followup.send(embed=embed)

def apply_footer(embed, guild):
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"{server_name}")
    return embed

# ========== /erlc vehicles ==========
@erlc_group.command(name="vehicles", description="Show vehicles currently in the server")
async def vehicles(interaction: discord.Interaction):
    await interaction.response.defer()
    global session
    try:
        headers = {"server-key": API_KEY, "Accept": "*/*"}

        async with session.get(f"{API_BASE}/players", headers=headers) as resp_players:
            if resp_players.status != 200:
                text = await resp_players.text()
                raise Exception(f"PRC API error {resp_players.status}: {text}")
            players = await resp_players.json()

        async with session.get(f"{API_BASE}/vehicles", headers=headers) as resp_vehicles:
            if resp_vehicles.status != 200:
                text = await resp_vehicles.text()
                raise Exception(f"PRC API error {resp_vehicles.status}: {text}")
            vehicles = await resp_vehicles.json()

    except Exception as e:
        return await interaction.followup.send(f"Error fetching or processing vehicles: {get_error_message(e)}")

    if not vehicles:
        embed = discord.Embed(
            title="Server Vehicles 0",
            description="> There are no active vehicles in your server.",
            color=discord.Color.blue()
        )
        embed = apply_footer(embed, interaction.guild)
        return await interaction.followup.send(embed=embed)

    players_dict = {p['Player'].split(":")[0]: p for p in players}
    matched = []

    for vehicle in vehicles:
        owner = vehicle.get("Owner")
        if not owner or owner not in players_dict:
            continue
        matched.append((vehicle, players_dict[owner]))

    matched.sort(key=lambda x: x[1]['Player'].split(":")[0].lower())

    description_lines = []
    for veh, plr in matched:
        username, roblox_id = plr['Player'].split(":", 1)
        description_lines.append(f"[{username}](https://roblox.com/users/{roblox_id}/profile) - {veh['Name']} **({veh['Texture']})**")

    embed = discord.Embed(
        title=f"Server Vehicles [{len(vehicles)}/{len(players)}]",
        description="\n".join(description_lines),
        color=discord.Color.blue()
    )
    embed = apply_footer(embed, interaction.guild)
    await interaction.followup.send(embed=embed)

# ========== /discord check ==========
@discord_group.command(name="check", description="Check if players in ER:LC are not in Discord")
async def check(interaction: discord.Interaction):
    await interaction.response.defer()
    global session

    def extract_roblox_name(name: str) -> str:
        return name.split(" | ", 1)[1].lower() if " | " in name else name.lower()

    try:
        headers = {"server-key": API_KEY, "Accept": "*/*"}
        async with session.get(f"{API_BASE}/players", headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"PRC API error {resp.status}: {text}")
            players = await resp.json()
    except Exception as e:
        return await interaction.followup.send(f"Error fetching PRC data: {get_error_message(e)}")

    if not players:
        embed = discord.Embed(
            title="No Players in ER:LC",
            description="> No players found in the server.",
            color=discord.Color.blue()
        )
        embed = apply_footer(embed, interaction.guild)
        return await interaction.followup.send(embed=embed)

    roblox_names_in_discord = set()
    for member in interaction.guild.members:
        for name_source in (member.name, member.display_name):
            roblox_names_in_discord.add(extract_roblox_name(name_source))

    missing_players = []
    for player in players:
        roblox_username, roblox_id = player['Player'].split(":", 1)
        if roblox_username.lower() not in roblox_names_in_discord:
            missing_players.append((roblox_username, roblox_id))

    description = (
        "> All players are in the Discord server."
        if not missing_players else
        "\n".join(f"> [{u}](https://roblox.com/users/{i}/profile)" for u, i in missing_players)
    )

    embed = discord.Embed(
        title="Players in ER:LC Not in Discord",
        description=description,
        color=discord.Color.blue()
    )
    embed = apply_footer(embed, interaction.guild)
    await interaction.followup.send(embed=embed)

# Close aiohttp session on exit
@atexit.register
def close_session():
    if session and not session.closed:
        bot.loop.run_until_complete(session.close())

# ===== Embed Helpers =====

def success_embed(title, desc, guild):
    embed = discord.Embed(title=title, description=desc, color=discord.Color.green())
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"{server_name}")
    return embed

def error_embed(title, desc, guild):
    embed = discord.Embed(title=title, description=desc, color=discord.Color.red())
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"{server_name}")
    return embed

def is_staff():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.manage_guild
    return app_commands.check(predicate)

@erlc_group.command(name="bans", description="Filter the bans of your server.")
@is_staff()
@app_commands.describe(username="Filter by Roblox username", user_id="Filter by Roblox user ID")
async def bans(
    interaction: discord.Interaction,
    username: typing.Optional[str] = None,
    user_id: typing.Optional[int] = None,
):
    await interaction.response.defer()

    url = "https://api.policeroleplay.community/v1/server/bans"
    headers = {
        "server-key": API_KEY,
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return await interaction.followup.send(
                    embed=discord.Embed(
                        title="PRC API Error",
                        description=f"Failed to fetch bans. Status code: {resp.status}",
                        color=discord.Color.blurple(),  # or your BLANK_COLOR
                    )
                )
            bans_data = await resp.json()  # dict: {PlayerId: PlayerName}

    embed = discord.Embed(color=discord.Color.blurple(), title="Bans", description="")
    status = username or user_id

    username_filter = username.lower() if username else None
    user_id_filter = str(user_id) if user_id else None

    old_embed = copy.copy(embed)
    embeds = [embed]

    for player_id, player_name in bans_data.items():
        if (username_filter and username_filter in player_name.lower()) or (user_id_filter and user_id_filter == player_id) or not status:
            embed = embeds[-1]
            if len(embed.description) > 3800:
                new_embed = copy.copy(old_embed)
                embeds.append(new_embed)
                embed = new_embed
            embed.description += f"> [{player_name} ({player_id})](https://roblox.com/users/{player_id}/profile)\n"

    if embeds[0].description.strip() == "":
        embeds[0].description = (
            "> This ban was not found."
            if status
            else "> No bans found on your server."
        )

    guild_icon = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None
    for embed in embeds:
        embed.set_author(name=interaction.guild.name, icon_url=guild_icon)
        if guild_icon:
            embed.set_thumbnail(url=guild_icon)
        embed.set_footer(text=f"{server_name}")

    for embed in embeds:
        await interaction.followup.send(embed=embed)

def roblox_link(player_str: str):
    """Returns [Name](link) or just name"""
    try:
        name, user_id = player_str.split(":")
        return f"[{name}](https://www.roblox.com/users/{user_id}/profile)"
    except:
        return player_str

async def fetch_modcalls():
    url = f"{API_BASE}/modcalls"
    headers = {
        "server-key": API_KEY,
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise Exception(f"Failed to fetch modcalls: HTTP {resp.status}")

async def fetch_killlogs():
    url = f"{API_BASE}/killlogs"
    headers = {
        "server-key": API_KEY,
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise Exception(f"Failed to fetch kill logs: HTTP {resp.status}")

@erlc_group.command(name="killlogs", description="Show recent kill logs")
async def killlogs(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        killlogs = await fetch_killlogs()

        embed = discord.Embed(
            title=f"{server_name} - Kill Logs",
            color=discord.Color.blue()
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(text=f"{server_name}")

        if not killlogs:
            embed.add_field(
                name="No Kill Logs Found",
                value="> No kills in this category.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return

        for entry in killlogs[:10]:
            killer = roblox_link(entry.get("Killer", "Unknown"))
            victim = roblox_link(entry.get("Victim", "Unknown"))
            weapon = entry.get("Weapon", "Unknown")
            timestamp = entry.get("Timestamp", 0)
            time_str = f"<t:{int(timestamp)}:R>"

            value_text = (
                f"> **Killer:** {killer}\n"
                f"> **Victim:** {victim}\n"
                f"> **Weapon:** `{weapon}`\n"
                f"> **Time:** {time_str}"
            )

            embed.add_field(
                name="\u200b",
                value=value_text,
                inline=False
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to fetch kill logs.\n{e}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)


@erlc_group.command(name="modcalls", description="Show recent moderator call logs")
async def modcalls(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        modcalls = await fetch_modcalls()

        embed = discord.Embed(
            title=f"{server_name} - Modcalls",
            color=discord.Color.blue()
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(text=f"{server_name}")

        if not modcalls:
            embed.add_field(
                name="No Modcalls Found",
                value="> No modcalls in this category.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return

        for entry in modcalls[:10]:
            caller = roblox_link(entry.get("Caller", "Unknown"))
            moderator_raw = entry.get("Moderator", "No responder")
            moderator = roblox_link(moderator_raw) if ":" in moderator_raw else moderator_raw
            timestamp = entry.get("Timestamp", 0)
            time_str = f"<t:{int(timestamp)}:R>"

            value_text = (
                f"> **Caller:** {caller}\n"
                f"> **Moderator:** {moderator}\n"
                f"> **Time:** {time_str}"
            )

            embed.add_field(
                name="\u200b",
                value=value_text,
                inline=False
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to fetch modcalls.\n{e}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

async def fetch_players():
    headers = {"server-key": API_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/players", headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return None

@erlc_group.command(name="callsigns", description="List all players and their callsigns on the ER:LC server")
async def erlc_callsigns(interaction: discord.Interaction):
    await interaction.response.defer()

    players = await fetch_players()
    if players is None:
        embed = discord.Embed(
            title="Error",
            description="Failed to fetch players from the server API.",
            color=discord.Color.red()
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text=f"{server_name}")
        await interaction.followup.send(embed=embed)
        return

    if len(players) == 0:
        embed = discord.Embed(
            title="No Players Found",
            description="There are no players currently on the server.",
            color=discord.Color.orange()
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text=f"{server_name}")
        await interaction.followup.send(embed=embed)
        return

    # Build the description listing all players
    description_lines = []
    for p in players:
        player_name = p["Player"].split(":")[0]
        callsign = p.get("Callsign") or "No callsign (civilian)"
        team = p.get("Team") or "Unknown"
        description_lines.append(
            f"**Team:** {team}\n**User:** {player_name}\n**Callsign:** {callsign}\n"
        )

    description = "\n".join(description_lines)

    embed = discord.Embed(
        title=f"{server_name} - callsigns",
        description=description,
        color=discord.Color.blue()
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text=f"{server_name}")

    await interaction.followup.send(embed=embed)



# -------- Bot Events --------
# on_ready event
@bot.event
async def on_ready():
    try:
        if not getattr(bot, "synced", False):
            await bot.tree.sync()
            bot.synced = True
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    bot.start_time = datetime.now(timezone.utc)
    await get_session()

    bot.loop.create_task(prc_event_loop())

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name="over the server")
    )
    print(f"{bot.user} is ready and watching over the server.")
    print("------------------------------------------------------------------")

@atexit.register
def close_session():
    if session and not session.closed:
        asyncio.run(session.close())

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
