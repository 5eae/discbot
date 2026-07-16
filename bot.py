import os
import json
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID", "0"))
VOUCH_CHANNEL_ID = int(os.getenv("VOUCH_CHANNEL_ID", "0"))
MOD_ROLE_ID = int(os.getenv("MOD_ROLE_ID", "0"))
VOUCHABLE_ROLE_ID = int(os.getenv("VOUCHABLE_ROLE_ID", "0"))
AUTOROLE_ID = int(os.getenv("AUTOROLE_ID", "0"))

DATA_FILE = "vouch_data.json"
GHOST_PING_FILE = "ghost_ping_channels.json"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------- simple JSON storage ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_vouch(user_id: int):
    data = load_data()
    key = str(user_id)
    data[key] = data.get(key, 0) + 1
    save_data(data)
    return data[key]


def get_vouches(user_id: int):
    data = load_data()
    return data.get(str(user_id), 0)


def load_ghost_channels():
    if not os.path.exists(GHOST_PING_FILE):
        return {}
    with open(GHOST_PING_FILE, "r") as f:
        return json.load(f)


def save_ghost_channels(data):
    with open(GHOST_PING_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_ghost_channel_ids(guild_id: int):
    data = load_ghost_channels()
    return data.get(str(guild_id), [])


def set_ghost_channel_ids(guild_id: int, channel_ids: list):
    data = load_ghost_channels()
    data[str(guild_id)] = channel_ids
    save_ghost_channels(data)


# ---------- payment method choices ----------
PAYMENT_CHOICES = [
    app_commands.Choice(name="PayPal", value="PayPal"),
    app_commands.Choice(name="Cash App", value="Cash App"),
    app_commands.Choice(name="Crypto", value="Crypto"),
    app_commands.Choice(name="Bank Transfer", value="Bank Transfer"),
    app_commands.Choice(name="Other", value="Other"),
]


def is_mod(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.manage_guild:
        return True
    if MOD_ROLE_ID and any(r.id == MOD_ROLE_ID for r in interaction.user.roles):
        return True
    return False


def is_vouchable(member: discord.Member) -> bool:
    if not VOUCHABLE_ROLE_ID:
        # If no role is configured, fall back to allowing anyone.
        return True
    return any(r.id == VOUCHABLE_ROLE_ID for r in member.roles)


# ---------- approval view ----------
class ApprovalView(discord.ui.View):
    def __init__(self, vouched_for: discord.Member, vouched_by: discord.Member,
                 videos: int, payment: str):
        super().__init__(timeout=None)
        self.vouched_for = vouched_for
        self.vouched_by = vouched_by
        self.videos = videos
        self.payment = payment

    def build_pending_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Vouch Pending Approval", color=discord.Color.gold())
        embed.add_field(name="Vouched For", value=self.vouched_for.mention, inline=True)
        embed.add_field(name="Vouched By", value=self.vouched_by.mention, inline=True)
        embed.add_field(name="Videos", value=str(self.videos), inline=True)
        embed.add_field(name="Payment Method", value=self.payment, inline=True)
        return embed

    def build_public_embed(self) -> discord.Embed:
        embed = discord.Embed(title="✅ New Vouch", color=discord.Color.green())
        embed.add_field(name="Vouched For", value=self.vouched_for.mention, inline=True)
        embed.add_field(name="Vouched By", value=self.vouched_by.mention, inline=True)
        embed.add_field(name="Videos", value=str(self.videos), inline=True)
        embed.add_field(name="Payment Method", value=self.payment, inline=True)
        return embed

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="vouch_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_mod(interaction):
            await interaction.response.send_message("You don't have permission to do that.", ephemeral=True)
            return

        total = add_vouch(self.vouched_for.id)

        public_channel = interaction.client.get_channel(VOUCH_CHANNEL_ID)
        if public_channel:
            embed = self.build_public_embed()
            embed.set_footer(text=f"Total vouches for {self.vouched_for.display_name}: {total}")
            await public_channel.send(embed=embed)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"✅ Approved by {interaction.user.mention}",
            embed=self.build_pending_embed(),
            view=self,
        )

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="vouch_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_mod(interaction):
            await interaction.response.send_message("You don't have permission to do that.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"❌ Denied by {interaction.user.mention}",
            embed=self.build_pending_embed(),
            view=self,
        )


def can_nuke(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.manage_messages:
        return True
    return is_mod(interaction)


class NukeConfirmView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel, requester_id: int):
        super().__init__(timeout=30)
        self.channel = channel
        self.requester_id = requester_id

    @discord.ui.button(label="Confirm Nuke", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester_id and not can_nuke(interaction):
            await interaction.response.send_message("You don't have permission to do that.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Nuking channel...", view=self)

        new_channel = await self.channel.clone(reason=f"Nuked by {interaction.user}")
        await new_channel.edit(position=self.channel.position)
        await self.channel.delete(reason=f"Nuked by {interaction.user}")
        await new_channel.send(f"💥 Channel nuked by {interaction.user.mention}")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Cancelled.", view=self)


class GhostPingSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select channel(s) to ghost-ping in (select none to disable)",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=25,
        )

    async def callback(self, interaction: discord.Interaction):
        channel_ids = [c.id for c in self.values]
        set_ghost_channel_ids(interaction.guild.id, channel_ids)
        if channel_ids:
            mentions = ", ".join(f"<#{cid}>" for cid in channel_ids)
            content = f"New members will now be ghost-pinged in: {mentions}"
        else:
            content = "Ghost-ping disabled — no channels selected."
        await interaction.response.edit_message(content=content, view=None)


class GhostPingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(GhostPingSelect())


@bot.tree.command(name="vouch", description="Submit a vouch for someone")
@app_commands.describe(
    user="Who are you vouching for?",
    videos="How many videos did they do?",
    payment="What payment method did you use?",
)
@app_commands.choices(payment=PAYMENT_CHOICES)
async def vouch(interaction: discord.Interaction, user: discord.Member, videos: int,
                 payment: app_commands.Choice[str]):
    if user.id == interaction.user.id:
        await interaction.response.send_message("You can't vouch for yourself.", ephemeral=True)
        return
    if not is_vouchable(user):
        await interaction.response.send_message(
            f"{user.mention} isn't eligible to receive vouches.", ephemeral=True
        )
        return
    if videos < 1:
        await interaction.response.send_message("Videos must be at least 1.", ephemeral=True)
        return

    mod_channel = bot.get_channel(MOD_CHANNEL_ID)
    if mod_channel is None:
        await interaction.response.send_message(
            "Mod approval channel isn't configured correctly. Contact an admin.", ephemeral=True
        )
        return

    view = ApprovalView(vouched_for=user, vouched_by=interaction.user, videos=videos, payment=payment.value)
    await mod_channel.send(embed=view.build_pending_embed(), view=view)

    await interaction.response.send_message(
        f"Your vouch for {user.mention} has been submitted for mod approval.", ephemeral=True
    )


@bot.tree.command(name="vouches", description="Check how many approved vouches someone has")
@app_commands.describe(user="Whose vouch count do you want to see? (defaults to you)")
async def vouches(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    count = get_vouches(target.id)
    await interaction.response.send_message(f"{target.mention} has **{count}** approved vouch(es).")


@bot.tree.command(name="nuke", description="Delete messages in this channel")
@app_commands.describe(amount="How many recent messages to delete (leave blank to wipe the entire channel)")
async def nuke(interaction: discord.Interaction, amount: int = None):
    if not can_nuke(interaction):
        await interaction.response.send_message("You don't have permission to do that.", ephemeral=True)
        return

    if amount is not None:
        if amount < 1:
            await interaction.response.send_message("Amount must be at least 1.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            f"Deleted {len(deleted)} message(s). Note: Discord only allows bulk-deleting "
            f"messages newer than 14 days — anything older won't be removed this way.",
            ephemeral=True,
        )
    else:
        view = NukeConfirmView(channel=interaction.channel, requester_id=interaction.user.id)
        await interaction.response.send_message(
            f"This will permanently delete **all messages** in {interaction.channel.mention} "
            f"by cloning it and deleting the original. Continue?",
            view=view,
            ephemeral=True,
        )


@bot.tree.command(name="mention", description="Choose which channels ghost-ping new members when they join")
async def mention(interaction: discord.Interaction):
    if not is_mod(interaction):
        await interaction.response.send_message("You don't have permission to do that.", ephemeral=True)
        return

    current = get_ghost_channel_ids(interaction.guild.id)
    if current:
        mentions = ", ".join(f"<#{cid}>" for cid in current)
        prefix = f"Currently ghost-pinging in: {mentions}\n\n"
    else:
        prefix = "Ghost-ping is currently disabled.\n\n"

    view = GhostPingView()
    await interaction.response.send_message(
        prefix + "Select the channel(s) new members should be ghost-pinged in (select none to disable):",
        view=view,
        ephemeral=True,
    )


@bot.event
async def on_member_join(member: discord.Member):
    if AUTOROLE_ID:
        role = member.guild.get_role(AUTOROLE_ID)
        if role is not None:
            try:
                await member.add_roles(role, reason="Autorole on join")
            except discord.Forbidden:
                print(f"Missing permission to assign autorole to {member}.")

    for channel_id in get_ghost_channel_ids(member.guild.id):
        channel = member.guild.get_channel(channel_id)
        if channel is None:
            continue
        try:
            ghost_msg = await channel.send(member.mention)
            await ghost_msg.delete()
        except discord.Forbidden:
            print(f"Missing permission to ghost-ping in {channel}.")
        except discord.HTTPException:
            pass


@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
        else:
            synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Command sync failed: {e}")
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in.")
    bot.run(TOKEN)
