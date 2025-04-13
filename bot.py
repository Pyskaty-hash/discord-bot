import discord
from discord.ext import commands, tasks
import json
from datetime import datetime, timedelta

# Ustawienia bota
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

data_file = 'szkolenia.json'

# === Funkcje pomocnicze ===

def load_data():
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
            if 'szkolenia' not in data:
                data['szkolenia'] = []
            return data
    except FileNotFoundError:
        return {"szkolenia": []}

def save_data(data):
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=4)

async def is_training_officer(interaction: discord.Interaction):
    member = interaction.user if isinstance(interaction.user, discord.Member) else await interaction.guild.fetch_member(interaction.user.id)
    return any(role.name == "Training Officer" for role in member.roles)

# === Komendy ===
@bot.tree.command(name="ustaw_szkolenie", description="Zmień datę lub opis istniejącego szkolenia")
async def ustaw_szkolenie(interaction: discord.Interaction, szkolenie_id: int, nowa_data: str = None, nowy_opis: str = None):
    if not await is_training_officer(interaction):
        await interaction.response.send_message("Nie masz uprawnień do edytowania szkoleń!", ephemeral=True)
        return

    szkolenia_data = load_data()
    szkolenie = next((s for s in szkolenia_data["szkolenia"] if s["id"] == str(szkolenie_id)), None)

    if not szkolenie:
        await interaction.response.send_message("Szkolenie o podanym ID nie istnieje!", ephemeral=True)
        return

    if szkolenie["officer_id"] != interaction.user.id:
        await interaction.response.send_message("Nie jesteś właścicielem tego szkolenia!", ephemeral=True)
        return

    if nowa_data:
        szkolenie["data"] = nowa_data
    if nowy_opis:
        szkolenie["opis"] = nowy_opis

    save_data(szkolenia_data)
    await interaction.response.send_message("✅ Szkolenie zostało zaktualizowane!")

@bot.tree.command(name="dodaj_szkolenie", description="Dodaj nowe szkolenie")
async def dodaj_szkolenie(interaction: discord.Interaction, data: str, opis: str):
    if not await is_training_officer(interaction):
        await interaction.response.send_message("Nie masz uprawnień do dodawania szkoleń!", ephemeral=True)
        return

    szkolenia_data = load_data()

    for szkolenie in szkolenia_data["szkolenia"]:
        if szkolenie["data"] == data:
            await interaction.response.send_message(f"Szkolenie w tym czasie już istnieje!", ephemeral=True)
            return

    szkolenie = {
        "id": str(len(szkolenia_data["szkolenia"]) + 1),
        "data": data,
        "opis": opis,
        "user_id": None,
        "officer_id": interaction.user.id,
        "status": "Brak",  # Status domyślny
        "zatwierdzenie": False  # Domyślnie niezatwierdzone
    }

    szkolenia_data["szkolenia"].append(szkolenie)
    save_data(szkolenia_data)

    await interaction.response.send_message(f"Szkolenie '{opis}' zostało dodane!")

@bot.tree.command(name="przypisz_uzytkownika", description="Przypisz użytkownika do szkolenia")
async def przypisz_uzytkownika(interaction: discord.Interaction, user: discord.User, szkolenie_id: int):
    if not await is_training_officer(interaction):
        await interaction.response.send_message("Nie masz uprawnień do przypisywania użytkowników!", ephemeral=True)
        return

    szkolenia_data = load_data()
    szkolenie = next((s for s in szkolenia_data["szkolenia"] if s["id"] == str(szkolenie_id)), None)

    if not szkolenie:
        await interaction.response.send_message("Szkolenie o podanym ID nie istnieje!", ephemeral=True)
        return

    if szkolenie["user_id"]:
        await interaction.response.send_message("Szkolenie jest już przypisane do innego użytkownika!", ephemeral=True)
        return

    szkolenie["user_id"] = user.id
    save_data(szkolenia_data)

    await interaction.response.send_message(f"Użytkownik {user.mention} został przypisany do szkolenia!")

@bot.tree.command(name="przenies_szkolenie", description="Przenieś przypisane szkolenie na innego użytkownika")
async def przenies_szkolenie(interaction: discord.Interaction, szkolenie_id: int, nowy_uzytkownik: discord.User):
    if not await is_training_officer(interaction):
        await interaction.response.send_message("Nie masz uprawnień do przenoszenia szkoleń!", ephemeral=True)
        return

    szkolenia_data = load_data()
    szkolenie = next((s for s in szkolenia_data["szkolenia"] if s["id"] == str(szkolenie_id)), None)

    if not szkolenie:
        await interaction.response.send_message("Szkolenie o podanym ID nie istnieje!", ephemeral=True)
        return

    if szkolenie["user_id"] is None:
        await interaction.response.send_message("Szkolenie nie ma przypisanego użytkownika!", ephemeral=True)
        return

    szkolenie["user_id"] = nowy_uzytkownik.id
    save_data(szkolenia_data)

    await interaction.response.send_message(f"Szkolenie zostało przeniesione na użytkownika {nowy_uzytkownik.mention}!")

@bot.tree.command(name="usun_przypisanie", description="Usuń przypisanie użytkownika do szkolenia")
async def usun_przypisanie(interaction: discord.Interaction, szkolenie_id: int):
    if not await is_training_officer(interaction):
        await interaction.response.send_message("Nie masz uprawnień do usuwania przypisań!", ephemeral=True)
        return

    szkolenia_data = load_data()
    szkolenie = next((s for s in szkolenia_data["szkolenia"] if s["id"] == str(szkolenie_id)), None)

    if not szkolenie:
        await interaction.response.send_message("Szkolenie o podanym ID nie istnieje!", ephemeral=True)
        return

    if szkolenie["user_id"] is None:
        await interaction.response.send_message("Szkolenie nie ma przypisanego użytkownika!", ephemeral=True)
        return

    szkolenie["user_id"] = None
    save_data(szkolenia_data)

    await interaction.response.send_message(f"Przypisanie użytkownika zostało usunięte z tego szkolenia!")

@bot.tree.command(name="moje_szkolenia", description="Sprawdź swoje szkolenia jako Training Officer")
async def moje_szkolenia(interaction: discord.Interaction):
    if not await is_training_officer(interaction):
        await interaction.response.send_message("Nie masz uprawnień do przeglądania szkoleń!", ephemeral=True)
        return

    szkolenia_data = load_data()
    szkolenia_officera = [s for s in szkolenia_data["szkolenia"] if s["officer_id"] == interaction.user.id]

    if not szkolenia_officera:
        await interaction.response.send_message("Nie masz przypisanych żadnych szkoleń!", ephemeral=True)
        return

    response = "Twoje szkolenia:\n"
    for s in szkolenia_officera:
        user = await bot.fetch_user(s["user_id"]) if s["user_id"] else "Brak przypisanego użytkownika"
        zatwierdzenie = "✅ Zatwierdzone" if s["zatwierdzenie"] else "❌ Niezatwierdzone"
        response += f"**{s['opis']}** - {s['data']} (Przypisany użytkownik: {user}) - Status: {s['status']} ({zatwierdzenie})\n"

    await interaction.response.send_message(response)

# === Przypomnienia ===

async def przypomnienie(szkolenie):
    user = await bot.fetch_user(szkolenie["user_id"])
    officer = await bot.fetch_user(szkolenie["officer_id"])
    szkolenie_time = datetime.strptime(szkolenie["data"], "%Y-%m-%dT%H:%M:%S")
    now = datetime.now()

    if szkolenie_time - timedelta(hours=1) <= now < szkolenie_time - timedelta(minutes=59):
        await user.send(f"🕐 Przypomnienie: Twoje szkolenie '{szkolenie['opis']}' rozpocznie się za 1 godzinę!")
        await officer.send(f"🕐 Szkolenie '{szkolenie['opis']}' rozpocznie się za 1 godzinę!")

    if szkolenie_time - timedelta(minutes=10) <= now < szkolenie_time - timedelta(minutes=9):
        await user.send(f"⏰ Przypomnienie: Twoje szkolenie '{szkolenie['opis']}' rozpocznie się za 10 minut!")
        await officer.send(f"⏰ Szkolenie '{szkolenie['opis']}' rozpocznie się za 10 minut!")

@tasks.loop(minutes=1)
async def przypomnienie_loop():
    szkolenia_data = load_data()
    for s in szkolenia_data["szkolenia"]:
        if s["user_id"]:  # Tylko przypisane szkolenia
            await przypomnienie(s)

# === Eventy ===

@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=1257397858055880855)  # Twój serwer testowy
        await bot.tree.sync(guild=guild)  # Synchronizacja komend z Discordem
        print(f'✅ Slash commands zsynchronizowane z serwerem ({guild.id})')
    except Exception as e:
        print(f'❌ Błąd synchronizacji komend: {e}')

    przypomnienie_loop.start()
    print(f'✅ Bot {bot.user} jest gotowy! (ID: {bot.user.id})')

# === Start ===

bot.run("MTM2MDkxNzU2NDA1MzY1NTYyOA.GLtHhR.HYGsDMWAlJIBgKvlnhlJBcKuvIF9TVS4KOFP68")
