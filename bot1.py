import discord
from discord.ext import commands
import sqlite3
import random
import os

TOKEN = os.environ.get("TOKEN")

# --- Database ---
conn = sqlite3.connect("giveaway.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        ticket_number INTEGER UNIQUE
    )
""")
conn.commit()

# --- Bot ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_unique_ticket():
    while True:
        number = random.randint(10000, 99999)
        cursor.execute("SELECT 1 FROM tickets WHERE ticket_number = ?", (number,))
        if not cursor.fetchone():
            return number

# --- Giveaway button ---
class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟️ Get Ticket", style=discord.ButtonStyle.success, custom_id="get_ticket")
    async def get_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        cursor.execute("SELECT ticket_number FROM tickets WHERE user_id = ?", (user.id,))
        row = cursor.fetchone()

        if row:
            await interaction.response.send_message(
                f"🎟️ You already have a ticket: **#{row[0]}**", ephemeral=True
            )
            return

        ticket = get_unique_ticket()
        cursor.execute(
            "INSERT INTO tickets (user_id, username, ticket_number) VALUES (?, ?, ?)",
            (user.id, str(user), ticket)
        )
        conn.commit()

        await interaction.response.send_message(
            f"✅ You're in the giveaway! Your ticket: **#{ticket}**", ephemeral=True
        )

# --- Admin panel ---
class AdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🏆 Pick Winner", style=discord.ButtonStyle.danger, custom_id="pick_winner")
    async def pick_winner(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ No access!", ephemeral=True)
            return

        cursor.execute("SELECT user_id, username, ticket_number FROM tickets")
        rows = cursor.fetchall()

        if not rows:
            await interaction.response.send_message("❌ No participants!", ephemeral=True)
            return

        user_id, username, ticket = random.choice(rows)
        await interaction.response.send_message(
            f"🏆 Winner: **{username}** with ticket **#{ticket}** (<@{user_id}>)!"
        )

    @discord.ui.button(label="👥 Participants", style=discord.ButtonStyle.secondary, custom_id="show_participants")
    async def show_participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ No access!", ephemeral=True)
            return

        cursor.execute("SELECT username, ticket_number FROM tickets")
        rows = cursor.fetchall()

        if not rows:
            await interaction.response.send_message("No participants yet.", ephemeral=True)
            return

        text = "\n".join([f"#{ticket} — {name}" for name, ticket in rows])
        await interaction.response.send_message(f"**Participants ({len(rows)}):**\n{text}", ephemeral=True)

    @discord.ui.button(label="🗑️ Reset", style=discord.ButtonStyle.danger, custom_id="reset_giveaway")
    async def reset_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ No access!", ephemeral=True)
            return

        cursor.execute("DELETE FROM tickets")
        conn.commit()
        await interaction.response.send_message("✅ Database cleared, ready for a new giveaway!", ephemeral=True)

# --- Events and commands ---
@bot.event
async def on_ready():
    print(f"✅ Bot is running: {bot.user}")
    bot.add_view(GiveawayView())
    bot.add_view(AdminView())

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="🎉 Giveaway",
        description="Click the button below to get your ticket and join the giveaway!",
        color=0x2b2d31
    )
    await ctx.send(embed=embed, view=GiveawayView())

@bot.command()
@commands.has_permissions(administrator=True)
async def admin(ctx):
    embed = discord.Embed(
        title="⚙️ Admin Panel",
        description="Giveaway management",
        color=0xff0000
    )
    await ctx.send(embed=embed, view=AdminView())

bot.run(TOKEN)
