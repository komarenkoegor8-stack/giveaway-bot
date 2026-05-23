import discord
from discord.ext import commands
import sqlite3
import random

import os
TOKEN = os.environ.get("TOKEN")

# --- База данных ---
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

# --- Бот ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_unique_ticket():
    while True:
        number = random.randint(10000, 99999)
        cursor.execute("SELECT 1 FROM tickets WHERE ticket_number = ?", (number,))
        if not cursor.fetchone():
            return number

# --- Кнопка для участников ---
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
                f"🎟️ У тебя уже есть билет: **#{row[0]}**", ephemeral=True
            )
            return

        ticket = get_unique_ticket()
        cursor.execute(
            "INSERT INTO tickets (user_id, username, ticket_number) VALUES (?, ?, ?)",
            (user.id, str(user), ticket)
        )
        conn.commit()

        await interaction.response.send_message(
            f"✅ Ты в розыгрыше! Твой билет: **#{ticket}**", ephemeral=True
        )

# --- Админ-панель ---
class AdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🏆 Выбрать победителя", style=discord.ButtonStyle.danger, custom_id="pick_winner")
    async def pick_winner(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Нет доступа!", ephemeral=True)
            return

        cursor.execute("SELECT user_id, username, ticket_number FROM tickets")
        rows = cursor.fetchall()

        if not rows:
            await interaction.response.send_message("❌ Нет участников!", ephemeral=True)
            return

        user_id, username, ticket = random.choice(rows)
        await interaction.response.send_message(
            f"🏆 Победитель: **{username}** с билетом **#{ticket}** (<@{user_id}>)!"
        )

    @discord.ui.button(label="👥 Участники", style=discord.ButtonStyle.secondary, custom_id="show_participants")
    async def show_participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Нет доступа!", ephemeral=True)
            return

        cursor.execute("SELECT username, ticket_number FROM tickets")
        rows = cursor.fetchall()

        if not rows:
            await interaction.response.send_message("Участников пока нет.", ephemeral=True)
            return

        text = "\n".join([f"#{ticket} — {name}" for name, ticket in rows])
        await interaction.response.send_message(f"**Участники ({len(rows)}):**\n{text}", ephemeral=True)

    @discord.ui.button(label="🗑️ Сбросить", style=discord.ButtonStyle.danger, custom_id="reset_giveaway")
    async def reset_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Нет доступа!", ephemeral=True)
            return

        cursor.execute("DELETE FROM tickets")
        conn.commit()
        await interaction.response.send_message("✅ База очищена, можно начинать новый розыгрыш!", ephemeral=True)

# --- События и команды ---
@bot.event
async def on_ready():
    print(f"✅ Бот запущен: {bot.user}")
    bot.add_view(GiveawayView())
    bot.add_view(AdminView())

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="🎉 Розыгрыш",
        description="Нажми кнопку ниже чтобы получить билет и участвовать в розыгрыше!",
        color=0x2b2d31
    )
    await ctx.send(embed=embed, view=GiveawayView())

@bot.command()
@commands.has_permissions(administrator=True)
async def admin(ctx):
    embed = discord.Embed(
        title="⚙️ Админ-панель",
        description="Управление розыгрышем",
        color=0xff0000
    )
    await ctx.send(embed=embed, view=AdminView())

bot.run(TOKEN)