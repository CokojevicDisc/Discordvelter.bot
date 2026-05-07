import discord
from discord import app_commands
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

STAFF_ROLES = [
    "Dev. Team",
    "Director",
    "Head Admin",
    "Senior Admin",
    "Administrator",
    "Moderator",
    "Game Support"
]


def has_staff_role(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(role.name in STAFF_ROLES for role in member.roles)


class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Mora biti ukljucen u Developer Portal -> Bot -> Message Content Intent
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketMenuView())
        self.add_view(CloseTicketView())
        await self.tree.sync()
        print("Slash komande su sinhronizovane.")

    async def on_ready(self):
        print(f"Bot je ulogovan kao {self.user} (ID: {self.user.id})")


bot = MyBot()


async def open_ticket_channel(guild, user, ticket_type, embed_info: discord.Embed):
    channel_name = f"ticket-{ticket_type}-{user.name}".lower().replace(" ", "-")

    existing = discord.utils.get(guild.text_channels, name=channel_name)
    if existing:
        return None, existing

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    for role_name in STAFF_ROLES:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )

    category = discord.utils.get(guild.categories, name="ASKQ & REPORT")
    channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        category=category
    )

    await channel.send(embed=embed_info, view=CloseTicketView())

    staff_mentions = []
    for role_name in STAFF_ROLES:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            staff_mentions.append(role.mention)
    if staff_mentions:
        await channel.send(" ".join(staff_mentions))

    return channel, None


class AskModal(discord.ui.Modal, title="❓ Ask Ticket"):
    nick = discord.ui.TextInput(
        label="Tvoj nick na serveru",
        placeholder="npr. Marko_Markovic",
        required=True,
        max_length=50
    )
    pitanje = discord.ui.TextInput(
        label="Šta ti treba od pomoći?",
        placeholder="Opiši što detaljnije...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="❓ ASK TICKET", color=0x00C853)
        embed.add_field(name="👤 Korisnik", value=interaction.user.mention, inline=True)
        embed.add_field(name="🎮 Nick na serveru", value=self.nick.value, inline=True)
        embed.add_field(name="❓ Šta treba pomoći", value=self.pitanje.value, inline=False)
        embed.set_footer(text="Klikni dugme ispod da zatvoriš ticket kada završiš.")

        channel, existing = await open_ticket_channel(interaction.guild, interaction.user, "ask", embed)
        if existing:
            await interaction.response.send_message(f"❌ Već imaš otvoren ticket: {existing.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ Ticket je otvoren: {channel.mention}", ephemeral=True)


class ReportModal(discord.ui.Modal, title="📋 Report Ticket"):
    nick = discord.ui.TextInput(
        label="Tvoj nick na serveru",
        placeholder="npr. Marko_Markovic",
        required=True,
        max_length=50
    )
    reported_nick = discord.ui.TextInput(
        label="Ime_Prezime igrača kojeg prijaviš",
        placeholder="npr. Stefan_Stefanovic",
        required=True,
        max_length=50
    )
    razlog = discord.ui.TextInput(
        label="Razlog prijave",
        placeholder="Opiši što detaljnije šta se desilo...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📋 REPORT TICKET", color=0xFF4444)
        embed.add_field(name="👤 Podnosilac", value=interaction.user.mention, inline=True)
        embed.add_field(name="🎮 Tvoj nick", value=self.nick.value, inline=True)
        embed.add_field(name="🚨 Prijavljeni igrač", value=self.reported_nick.value, inline=True)
        embed.add_field(name="📄 Razlog prijave", value=self.razlog.value, inline=False)
        embed.set_footer(text="Klikni dugme ispod da zatvoriš ticket kada završiš.")

        channel, existing = await open_ticket_channel(interaction.guild, interaction.user, "report", embed)
        if existing:
            await interaction.response.send_message(f"❌ Već imaš otvoren ticket: {existing.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ Ticket je otvoren: {channel.mention}", ephemeral=True)


class TicketMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Report", style=discord.ButtonStyle.danger, custom_id="ticket_report")
    async def report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReportModal())

    @discord.ui.button(label="❓ Ask", style=discord.ButtonStyle.success, custom_id="ticket_ask")
    async def ask_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AskModal())


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Zatvori ticket", style=discord.ButtonStyle.secondary, custom_id="ticket_close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔒 Ticket zatvoren",
            description=f"Ticket je zatvorio {interaction.user.mention}. Kanal će biti obrisan za 5 sekundi.",
            color=0x808080
        )
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()


@bot.tree.command(name="ticketstart", description="Pošalje embed sa ticket sistemom u trenutni kanal")
async def ticketstart(interaction: discord.Interaction):
    if not has_staff_role(interaction.user):
        await interaction.response.send_message("❌ Nemaš dozvolu da koristiš ovu komandu!", ephemeral=True)
        return
    embed = discord.Embed(
        title="🎫 TICKET SISTEM",
        description=(
            "Ukoliko imaš problem ili pitanje, otvori ticket klikom na odgovarajuće dugme ispod.\n\n"
            "📋 **Report** — Prijavi igrača ili problem na serveru\n"
            "❓ **Ask** — Postavi pitanje staff timu\n\n"
            "⚠️ Molimo te da ne otvараš ticket bez razloga."
        ),
        color=0x00C853
    )
    embed.set_footer(text="Velter Roleplay | Ticket Sistem")
    await interaction.response.send_message("✅ Ticket sistem je pokrenut!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=TicketMenuView())


@bot.tree.command(name="pravilastart", description="Pošalje embed sa pravilima servera u trenutni kanal")
async def pravilastart(interaction: discord.Interaction):
    if not has_staff_role(interaction.user):
        await interaction.response.send_message("❌ Nemaš dozvolu da koristiš ovu komandu!", ephemeral=True)
        return
    embed = discord.Embed(
        title="💚 VELTER ROLEPLAY | DISCORD PRAVILA 💚",
        description="Dobrodošli na **Velter Roleplay** Discord zajednicu 💚\nMolimo sve članove da poštuju pravila kako bi server bio prijatan, organizovan i aktivan.",
        color=0x00C853
    )
    embed.add_field(
        name="💚 1. OPŠTA PRAVILA",
        value=(
            "💚 Poštuj sve članove servera\n"
            "⚠️ Zabranjeno vređanje, rasizam i diskriminacija\n"
            "🛡️ Poštuj administraciju i njihove odluke\n"
            "🚫 Bez izazivanja svađa i nepotrebne drame\n"
            "📉 Spam i flood nisu dozvoljeni"
        ),
        inline=False
    )
    embed.add_field(
        name="💬 2. PONAŠANJE NA DISCORDU",
        value=(
            "💚 Koristi kanale za njihovu namenu\n"
            "🔞 NSFW sadržaj je strogo zabranjen\n"
            "📢 Reklamiranje bez dozvole nije dozvoljeno\n"
            "❗ Nemoj tagovati staff bez potrebe\n"
            "✍️ Piši kulturno i razumljivo"
        ),
        inline=False
    )
    embed.add_field(
        name="🎧 3. VOICE CHAT PRAVILA",
        value=(
            "🔊 Bez deranja i prevelike buke\n"
            "🎵 Zabranjeno puštanje muzike bez dozvole\n"
            "🤝 Poštuj ostale u voice kanalima\n"
            "🚫 Trollovanje u voice-u nije dozvoljeno"
        ),
        inline=False
    )
    embed.add_field(
        name="🛡️ 4. ADMINISTRACIJA",
        value=(
            "💚 Staff tim ima pravo da opomene ili kazni članove\n"
            "⚖️ Raspravljanje sa adminima javno nije dozvoljeno\n"
            "🎫 Žalbe se šalju isključivo preko ticket sistema\n"
            "📌 Odluke staff tima su konačne"
        ),
        inline=False
    )
    embed.add_field(
        name="🚫 5. ZABRANJENO JE",
        value=(
            "❌ Spam i bespotrebne poruke\n"
            "❌ Vređanje i provokacije\n"
            "🔞 NSFW sadržaj\n"
            "💸 Scam i prevare\n"
            "🔒 Deljenje tuđih ličnih podataka"
        ),
        inline=False
    )
    embed.add_field(
        name="⚠️ 6. KAZNE",
        value=(
            "Kršenje pravila može dovesti do:\n"
            "🟡 Warn\n"
            "🔇 Mute\n"
            "👢 Kick\n"
            "⛔ Ban"
        ),
        inline=False
    )
    embed.add_field(
        name="💚 7. CILJ ZAJEDNICE",
        value=(
            "Naš cilj je da zajedno napravimo:\n"
            "💚 aktivnu i zdravu zajednicu\n"
            "🌍 prijateljsku atmosferu\n"
            "🤝 poštovanje među članovima\n"
            "🎮 kvalitetan i uređen Discord server"
        ),
        inline=False
    )
    embed.set_footer(text="💚 Hvala ti što si deo Velter Roleplay zajednice i što pomažeš da server bude bolji za sve!")
    await interaction.response.send_message("✅ Pravila su poslata!", ephemeral=True)
    await interaction.channel.send(embed=embed)



class ObavestenieModal(discord.ui.Modal, title="📢 Novo obaveštenje"):
    naslov = discord.ui.TextInput(
        label="Naslov obaveštenja",
        placeholder="npr. Važno obaveštenje!",
        required=True,
        max_length=100
    )
    tekst = discord.ui.TextInput(
        label="Tekst obaveštenja",
        placeholder="Upiši tekst koji želiš da pošalješ...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"📢 {self.naslov.value}",
            description=self.tekst.value,
            color=0x00C853
        )
        embed.set_footer(text=f"Obaveštenje poslao: {interaction.user.name}")
        await interaction.response.send_message("✅ Obaveštenje je poslato!", ephemeral=True)
        await interaction.channel.send(embed=embed)


@bot.tree.command(name="new", description="Pošalje embed obaveštenje u trenutni kanal")
async def new(interaction: discord.Interaction):
    if not has_staff_role(interaction.user):
        await interaction.response.send_message("❌ Nemaš dozvolu da koristiš ovu komandu!", ephemeral=True)
        return
    await interaction.response.send_modal(ObavestenieModal())


IMAGE_CHANNEL_NAME = "「📸」images-from-server"

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.channel.name == IMAGE_CHANNEL_NAME:
        if not message.attachments:
            await message.delete()


if __name__ == "__main__":
    if not TOKEN:
        print("GREŠKA: DISCORD_TOKEN nije postavljen!")
        exit(1)
    bot.run(TOKEN)
