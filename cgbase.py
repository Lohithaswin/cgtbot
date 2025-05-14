import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import os
import json
import datetime
import re as regex

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# File paths for persistent storage
DATA_DIR = "bot_data"
TEAMS_FILE = os.path.join(DATA_DIR, "teams_data.json")
FIXTURES_FILE = os.path.join(DATA_DIR, "fixtures.json")
UNDO_FILE = os.path.join(DATA_DIR, "undo_stack.json")
PLAYERS_FILE = os.path.join(DATA_DIR, "players.json")
ACTIVE_MATCHES_FILE = os.path.join(DATA_DIR, "active_matches.json")
HEAD_TO_HEAD_FILE = os.path.join(DATA_DIR, "head_to_head.json")

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize active matches file if missing
if not os.path.exists(ACTIVE_MATCHES_FILE):
    with open(ACTIVE_MATCHES_FILE, "w") as f:
        json.dump([], f)

# Ensure head_to_head is initialized at the top
if os.path.exists(HEAD_TO_HEAD_FILE):
    with open(HEAD_TO_HEAD_FILE, "r") as f:
        content = f.read().strip()
        if content:
            head_to_head = json.loads(content)
        else:
            head_to_head = {}
else:
    head_to_head = {}

# At the top of the file, after other global variables
global player_stats
player_stats = {}


# Add at the top with other global variables
match_counter = 0

match_state = {}  # key: match_id, value: dict with prev_striker, current_striker, etc.

# Function to load data from JSON files
def load_data():
    global teams_data, fixtures, undo_stack, active_matches, player_stats
    
    # Load teams data
    if os.path.exists(TEAMS_FILE):
        with open(TEAMS_FILE, 'r') as f:
            teams_data = json.load(f)
    else:
        teams_data = {
            "VLA's Super Leos 🦁": {"matches": 0, "wins": 0, "losses": 0, "points": 0, "runs_scored": 0, "overs_faced": 0.0, "runs_conceded": 0, "overs_bowled": 0.0, "nrr": 0.0},
            "POGS 🦊": {"matches": 0, "wins": 0, "losses": 0, "points": 0, "runs_scored": 0, "overs_faced": 0.0, "runs_conceded": 0, "overs_bowled": 0.0, "nrr": 0.0},
            "Bazz Bulls": {"matches": 0, "wins": 0, "losses": 0, "points": 0, "runs_scored": 0, "overs_faced": 0.0, "runs_conceded": 0, "overs_bowled": 0.0, "nrr": 0.0},
            "Chennai Tigers 🐯": {"matches": 0, "wins": 0, "losses": 0, "points": 0, "runs_scored": 0, "overs_faced": 0.0, "runs_conceded": 0, "overs_bowled": 0.0, "nrr": 0.0},
        }
    
    # Load player stats
    if os.path.exists(PLAYERS_FILE):
        with open(PLAYERS_FILE, 'r') as f:
            player_stats = json.load(f)
    else:
        player_stats = {}
    
    # Load fixtures
    if os.path.exists(FIXTURES_FILE):
        with open(FIXTURES_FILE, 'r') as f:
            fixtures = json.load(f)
    else:
        fixtures = [
            {"match": "Match 1", "teams": "VLA's Super Leos 🦁 vs Chennai Tigers 🐯", "result": "TBD"},
            {"match": "Match 2", "teams": "POGS 🦊 vs Bazz Bulls", "result": "TBD"},
        ]
    
    # Load undo stack
    if os.path.exists(UNDO_FILE):
        with open(UNDO_FILE, 'r') as f:
            undo_stack = json.load(f)
    else:
        undo_stack = []

    # Load active matches
    if os.path.exists(ACTIVE_MATCHES_FILE):
        with open(ACTIVE_MATCHES_FILE, 'r') as f:
            active_matches = json.load(f)
    else:
        active_matches = []

# Function to save data to JSON files
def save_data():
    with open(TEAMS_FILE, 'w') as f:
        json.dump(teams_data, f, indent=4)
    
    with open(FIXTURES_FILE, 'w') as f:
        json.dump(fixtures, f, indent=4)
    
    with open(UNDO_FILE, 'w') as f:
        json.dump(undo_stack, f, indent=4)

    with open(ACTIVE_MATCHES_FILE, 'w') as f:
        json.dump(active_matches, f, indent=4)

# Load initial data
load_data()

# Team data structure with cumulative stats for NRR calculation
if 'teams_data' not in globals():
    teams_data = {
        "VLA's Super Leos 🦁": {"matches": 0, "wins": 0, "losses": 0, "points": 0, "runs_scored": 0, "overs_faced": 0.0, "runs_conceded": 0, "overs_bowled": 0.0, "nrr": 0.0},
        "POGS 🦊": {"matches": 0, "wins": 0, "losses": 0, "points": 0, "runs_scored": 0, "overs_faced": 0.0, "runs_conceded": 0, "overs_bowled": 0.0, "nrr": 0.0},
        "Bazz Bulls": {"matches": 0, "wins": 0, "losses": 0, "points": 0, "runs_scored": 0, "overs_faced": 0.0, "runs_conceded": 0, "overs_bowled": 0.0, "nrr": 0.0},
        "Chennai Tigers 🐯": {"matches": 0, "wins": 0, "losses": 0, "points": 0, "runs_scored": 0, "overs_faced": 0.0, "runs_conceded": 0, "overs_bowled": 0.0, "nrr": 0.0},
    }

# Undo stack to revert the last update
if 'undo_stack' not in globals():
    undo_stack = []

# Tournament fixtures
if 'fixtures' not in globals():
    fixtures = [
        {"match": "Match 1", "teams": "VLA's Super Leos 🦁 vs Chennai Tigers 🐯", "result": "TBD"},
        {"match": "Match 2", "teams": "POGS 🦊 vs Bazz Bulls", "result": "TBD"},
    ]

# Helper function to find a team by its short name
def find_team(team_name):
    team_name = team_name.lower()
    for team in teams_data:
        if team_name == team[:3].lower():
            return team
    return None

# Function to calculate NRR for a team
def calculate_nrr(team):
    stats = teams_data[team]
    if stats["overs_faced"] > 0 and stats["overs_bowled"] > 0:
        nrr = (stats["runs_scored"] / stats["overs_faced"]) - (stats["runs_conceded"] / stats["overs_bowled"])
        return round(nrr, 2)
    return 0.0

# Generate the points table image
def generate_points_table_image(output_file="points_table.png"):
    # Image dimensions and styles
    width, height = 800, 400
    bg_color = (30, 30, 30)
    header_color = (50, 120, 200)
    text_color = (255, 255, 255)
    row_color = (45, 45, 45)
    border_color = (255, 255, 255)
    font_path = "arial.ttf"  # Replace with the path to a suitable .ttf font

    # Create the image
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    # Load the font
    font = ImageFont.truetype(font_path, 20)

    # Header settings
    header_height = 50
    column_widths = [300, 100, 100, 100, 100, 100]
    columns = ["Team Name", "Matches", "Wins", "Losses", "Points", "NRR"]

    # Draw the header
    draw.rectangle([(0, 0), (width, header_height)], fill=header_color)
    x_offset = 10
    for i, column in enumerate(columns):
        draw.text((x_offset, 10), column, fill=text_color, font=font)
        x_offset += column_widths[i]

    # Draw team rows
    y_offset = header_height
    sorted_teams = sorted(teams_data.items(), key=lambda x: (x[1]["points"], x[1]["nrr"]), reverse=True)
    for team, stats in sorted_teams:
        draw.rectangle([(0, y_offset), (width, y_offset + 40)], fill=row_color if (y_offset // 40) % 2 == 0 else bg_color)
        x_offset = 10
        values = [team, stats["matches"], stats["wins"], stats["losses"], stats["points"], f"{stats['nrr']:.2f}"]
        for i, value in enumerate(values):
            draw.text((x_offset, y_offset + 10), str(value), fill=text_color, font=font)
            x_offset += column_widths[i]
        y_offset += 40

    # Draw the border
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=border_color, width=2)

    # Save the image
    image.save(output_file)

def generate_leaderboard_image(output_file="leaderboard.png"):
    from PIL import ImageOps

    with open(PLAYERS_FILE, "r") as f:
        stats = json.load(f)

    with open("player_team_map.json", "r") as f:
        player_teams = json.load(f)

    top_batters = []
    for name, data in stats.items():
        runs = data.get("runs", 0)
        balls = data.get("balls", 0)
        sr = (runs / balls * 100) if balls > 0 else 0
        top_batters.append((name, runs, sr))
    top_batters.sort(key=lambda x: (-x[1], -x[2]))
    top_batters = top_batters[:10]

    top_bowlers = []
    for name, data in stats.items():
        wickets = data.get("wickets", 0)
        balls = data.get("balls", 0)
        runs_conceded = data.get("runs_conceded", 0)
        overs = balls / 6 if balls else 0
        economy = (runs_conceded / overs) if overs > 0 else 0
        top_bowlers.append((name, wickets, economy))
    top_bowlers.sort(key=lambda x: (-x[1], x[2]))
    top_bowlers = top_bowlers[:10]

    width, height = 950, 1100
    image = Image.new("RGB", (width, height), (20, 20, 20))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 22)
    title_font = ImageFont.truetype("arial.ttf", 30)

    draw.text((width//2 - 250, 20), "🏏 Cricket Guru Top 10 Leaderboard", fill=(255, 215, 0), font=title_font)

    def draw_section(title, data, start_y, label_color):
        draw.text((50, start_y), title, fill=label_color, font=title_font)
        y = start_y + 50
        for i, (name, val1, val2) in enumerate(data):
            avatar_path = f"assets/avatars/{name}.png"
            if not os.path.exists(avatar_path):
                avatar_path = f"assets/avatars/{name}.jpg"
            if os.path.exists(avatar_path):
                avatar = Image.open(avatar_path).convert("RGBA")
                avatar = avatar.resize((50, 50))
                avatar = ImageOps.fit(avatar, (50, 50), centering=(0.5, 0.5))
                image.paste(avatar, (60, y), avatar)

            team_code = player_teams.get(name, "")
            logo_path = f"assets/logos/{team_code}.png"
            if os.path.exists(logo_path):
                logo = Image.open(logo_path).convert("RGBA")
                logo = logo.resize((40, 40))
                image.paste(logo, (120, y + 5), logo)

            draw.text((180, y + 10), f"{i+1}. {name}", fill=(255, 255, 255), font=font)
            stat_text = f"{val1} runs, SR: {val2:.2f}" if title == "Top Batters" else f"{val1} wickets, Econ: {val2:.2f}"
            draw.text((550, y + 10), stat_text, fill=(200, 200, 200), font=font)
            y += 60

    draw_section("Top Batters", top_batters, 80, (0, 255, 0))
    draw_section("Top Bowlers", top_bowlers, 760, (255, 100, 100))
    image.save(output_file)

# Command to display the points table
@bot.command(aliases=["table", "pt"])
async def points_table(ctx):
    """Generate and display the points table."""
    generate_points_table_image()
    with open("points_table.png", "rb") as file:
        await ctx.send(file=discord.File(file, "points_table.png"))

# Command to update a team's stats
@bot.command(aliases=["upd"])
async def update(ctx, team: str = None, result: str = None, runs_scored: int = None, overs_faced: float = None, runs_conceded: int = None, overs_bowled: float = None):
    """Update team stats."""
    if None in [team, result, runs_scored, overs_faced, runs_conceded, overs_bowled]:
        await ctx.send("Syntax: !update <team> <win/loss> <runs_scored> <overs_faced> <runs_conceded> <overs_bowled>")
        return

    team = find_team(team)
    if not team:
        await ctx.send(embed=discord.Embed(title="Error", description="Team not found. Use the first three letters of a valid team (e.g., 'VLA' for VLA's Super Leos).", color=discord.Color.red()))
        return

    undo_stack.append(teams_data.copy())  # Save current state for undo

    stats = teams_data[team]
    stats["matches"] += 1
    stats["runs_scored"] += runs_scored
    stats["overs_faced"] += overs_faced
    stats["runs_conceded"] += runs_conceded
    stats["overs_bowled"] += overs_bowled

    if result.lower() == "win":
        stats["wins"] += 1
        stats["points"] += 2
    elif result.lower() == "loss":
        stats["losses"] += 1
    else:
        await ctx.send(embed=discord.Embed(title="Error", description="Invalid result. Use 'win' or 'loss'.", color=discord.Color.red()))
        return

    # Recalculate NRR
    stats["nrr"] = calculate_nrr(team)
    save_data()  # Save after updating
    await ctx.send(embed=discord.Embed(title="Success", description=f"Updated stats for {team}. Use !points_table to view the updated table.", color=discord.Color.green()))

# Command to reset the points table
@bot.command(aliases=["rst"])
async def reset(ctx):
    """Reset the points table."""
    global teams_data, undo_stack
    teams_data = {team: {"matches": 0, "wins": 0, "losses": 0, "points": 0, "runs_scored": 0, "overs_faced": 0.0, "runs_conceded": 0, "overs_bowled": 0.0, "nrr": 0.0} for team in teams_data}
    undo_stack.clear()
    save_data()  # Save after resetting
    await ctx.send(embed=discord.Embed(title="Success", description="The points table has been reset. Use !points_table to view the current table.", color=discord.Color.green()))

# Command to undo the last update
@bot.command(aliases=["undo_last"])
async def undo(ctx):
    """Undo the last update."""
    global teams_data
    if undo_stack:
        teams_data = undo_stack.pop()
        save_data()  # Save after undoing
        await ctx.send(embed=discord.Embed(title="Success", description="The last update has been undone. Use !points_table to view the current table.", color=discord.Color.green()))
    else:
        await ctx.send(embed=discord.Embed(title="Error", description="No updates to undo.", color=discord.Color.red()))

# Command to display about menu
@bot.command(aliases=["about", "info"])
async def help(ctx):
    """Display the about menu."""
    embed = discord.Embed(title="Cricket Guru Bot 🏏", color=discord.Color.blue())
    embed.add_field(name="Commands", value="""
    !points_table / !table / !pt: Show the current points table.
    !update / !upd: Update team stats. Format: !update <team> <win/loss> <runs_scored> <overs_faced> <runs_conceded> <overs_bowled>
    !reset / !rst: Reset the points table.
    !undo / !undo_last: Undo the last update.
    !sh / !schedule: Display the tournament schedule.
    !re / !result: Update match results and reflect in the schedule image.
    !mr: View all previous matches.
    !ct: Countdown and start the match with a cricket emoji.
    !leaderboard / !lb: Show top 5 batters and bowlers.
    !stats / !player <player>: Show stats for a specific player.
    !startmatch / !start: Start tracking a new match.
    !endmatch / !end [match_id]: End tracking a match (optional match_id).
    !matchstatus / !status: Show all active matches.
    !h2h <batter> <bowler>: View head-to-head stats for a batter vs bowler.
    """, inline=False)
    embed.set_footer(text="Enjoy managing your cricket tournament with Cricket Guru Bot!")
    await ctx.send(embed=embed)

# Countdown command
@bot.command(aliases=["countdown"])
async def ct(ctx):
    """Start a countdown."""
    for i in range(5, 0, -1):
        await ctx.send(f"{i}...")
    await ctx.send("LET'S PLAY! 🏏")

# Command to display the schedule
@bot.command(aliases=["schedule"])
async def sh(ctx):
    """Display the tournament schedule."""
    embed = discord.Embed(title="Tournament Schedule 🏏", color=discord.Color.gold())
    
    # Add all the fixtures here
    embed.add_field(name="Match 1", value="VLA's Super Leos 🦁 vs Chennai Tigers 🐯", inline=False)
    embed.add_field(name="Match 2", value="POGS 🦊 vs Bazz Bulls", inline=False)
    embed.add_field(name="Match 3", value="VLA's Super Leos 🦁 vs POGS 🦊", inline=False)
    embed.add_field(name="Match 4", value="Chennai Tigers 🐯 vs Bazz Bulls", inline=False)
    embed.add_field(name="Match 5", value="VLA's Super Leos 🦁 vs Bazz Bulls", inline=False)
    embed.add_field(name="Match 6", value="POGS 🦊 vs Chennai Tigers 🐯", inline=False)

    # Footer with instructions
    embed.set_footer(text="Use !re to update match results and reflect them in the schedule.")
    await ctx.send(embed=embed)


# Command to update the schedule
@bot.command(aliases=["result"])
async def re(ctx, winner: str = None, loser: str = None, by: str = None):
    """Update match results in the schedule."""
    if None in [winner, loser, by]:
        await ctx.send("Syntax: !re <winner> <loser> <margin>")
        return

    winner_team = find_team(winner)
    loser_team = find_team(loser)

    if not winner_team or not loser_team:
        await ctx.send(embed=discord.Embed(title="Error", description="Invalid teams. Use short names (e.g., 'VLA' for VLA's Super Leos).", color=discord.Color.red()))
        return

    for match in fixtures:
        if winner_team in match["teams"] and loser_team in match["teams"]:
            match["result"] = f"{winner_team} won by {by}"
            break

    embed = discord.Embed(title="Match Result 🏏", color=discord.Color.green())
    embed.add_field(name="Winner", value=winner_team, inline=True)
    embed.add_field(name="Loser", value=loser_team, inline=True)
    embed.add_field(name="Margin", value=f"Won by {by}", inline=False)
    embed.set_footer(text="The schedule has been updated.")
    await ctx.send(embed=embed)

# Command to view previous matches
@bot.command(aliases=["matches"])
async def mr(ctx):
    """View all previous matches."""
    embed = discord.Embed(title="Previous Matches 🏏", color=discord.Color.orange())
    for match in fixtures:
        if match["result"] != "TBD":
            embed.add_field(name=match["match"], value=f"{match['teams']}\nResult: {match['result']}", inline=False)
    embed.set_footer(text="Use !sh to view all fixtures.")
    save_data()
    await ctx.send(embed=embed)
   

# Event to signal bot readiness
@bot.event
async def on_ready():
    print(f"Bot is ready! Logged in as {bot.user}")

# Initialize player stats file if missing
if not os.path.exists(PLAYERS_FILE):
    with open(PLAYERS_FILE, "w") as f:
        json.dump({}, f)

def update_stats(player, runs=0, wickets=0, balls=0, match_id=None, bowler=None, is_dismissal=False, runs_conceded=0):
    with open(PLAYERS_FILE, "r") as f:
        stats = json.load(f)

    if player not in stats:
        stats[player] = {"runs": 0, "wickets": 0, "balls": 0, "matches": {}, "runs_conceded": 0}

    if "matches" not in stats[player]:
        stats[player]["matches"] = {}

    if match_id:
        # For match-specific updates, store in the match data
        if match_id not in stats[player]["matches"]:
            stats[player]["matches"][match_id] = {"runs": 0, "wickets": 0, "balls": 0, "runs_conceded": 0}
        
        # Update match stats (adding to existing values)
        stats[player]["matches"][match_id]["runs"] = runs
        stats[player]["matches"][match_id]["wickets"] = wickets
        stats[player]["matches"][match_id]["balls"] = balls
        stats[player]["matches"][match_id]["runs_conceded"] = runs_conceded
    else:
        # Direct updates without match_id - just add directly
        stats[player]["runs"] += runs
        stats[player]["wickets"] += wickets
        stats[player]["balls"] += balls
        stats[player]["runs_conceded"] += runs_conceded
        
        with open(PLAYERS_FILE, "w") as f:
            json.dump(stats, f, indent=4)
        
        if bowler:
            update_head_to_head(player, bowler, runs, balls, match_id, is_dismissal)
        return

    # Recalculate totals from matches - THIS IS THE KEY FIX
    # Instead of adding to totals, we'll recalculate from the match data
    total_runs = sum(m.get("runs", 0) for m in stats[player]["matches"].values())
    total_wickets = sum(m.get("wickets", 0) for m in stats[player]["matches"].values())
    total_balls = sum(m.get("balls", 0) for m in stats[player]["matches"].values())
    total_runs_conceded = sum(m.get("runs_conceded", 0) for m in stats[player]["matches"].values())

    # Set the totals instead of incrementing them
    stats[player]["runs"] = total_runs
    stats[player]["wickets"] = total_wickets
    stats[player]["balls"] = total_balls
    stats[player]["runs_conceded"] = total_runs_conceded

    with open(PLAYERS_FILE, "w") as f:
        json.dump(stats, f, indent=4)
    
    if bowler:
        update_head_to_head(player, bowler, runs, balls, match_id, is_dismissal)

# Command to reset player stats
@bot.command(aliases=["resetstats"])
async def reset_player_stats(ctx):
    """Reset all player statistics."""
    try:
        with open(PLAYERS_FILE, "w") as f:
            json.dump({}, f)
        await ctx.send(embed=discord.Embed(title="Success", description="All player statistics have been reset.", color=discord.Color.green()))
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"Failed to reset player stats: {str(e)}", color=discord.Color.red()))

# Command to fix player stats
@bot.command(aliases=["fixstats"])
async def fix_player_stats(ctx):
    """Fix player statistics by recalculating from match data."""
    try:
        with open(PLAYERS_FILE, "r") as f:
            stats = json.load(f)
        
        # For each player, recalculate totals from their match data
        for player in stats:
            if "matches" in stats[player]:
                stats[player]["runs"] = sum(m.get("runs", 0) for m in stats[player]["matches"].values())
                stats[player]["wickets"] = sum(m.get("wickets", 0) for m in stats[player]["matches"].values())
                stats[player]["balls"] = sum(m.get("balls", 0) for m in stats[player]["matches"].values())
                stats[player]["runs_conceded"] = sum(m.get("runs_conceded", 0) for m in stats[player]["matches"].values())
        
        with open(PLAYERS_FILE, "w") as f:
            json.dump(stats, f, indent=4)
            
        await ctx.send(embed=discord.Embed(title="Success", description="Player statistics have been recalculated and fixed.", color=discord.Color.green()))
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"Failed to fix player stats: {str(e)}", color=discord.Color.red()))

# Update stats utility (now also tracks runs_conceded for bowlers)
def update_head_to_head(batter, bowler, runs, balls, match_id, is_dismissal=False, append=True):
    """
    Update the head-to-head statistics between a batter and bowler.
    
    Parameters:
    - batter: The batter's name (canonical form preferred)
    - bowler: The bowler's name (canonical form preferred)
    - runs: Runs scored by batter off this bowler in this instance
    - balls: Balls faced by batter off this bowler in this instance 
    - match_id: Unique identifier for the current match
    - is_dismissal: True if this update represents a wicket
    - append: If True, add to existing stats; if False, replace stats
    """
    global head_to_head
    
    # Create key for the head-to-head record
    key = f"{batter} vs {bowler}"
    
    # Initialize record if it doesn't exist
    if key not in head_to_head:
        head_to_head[key] = {
            "matches": {},
            "runs": 0,
            "balls": 0,
            "dismissals": 0
        }
    
    # Initialize match record if it doesn't exist
    if match_id not in head_to_head[key]["matches"]:
        head_to_head[key]["matches"][match_id] = {
            "runs": 0,
            "balls": 0,
            "dismissals": 0
        }
    
    # Get match-specific stats
    match_stats = head_to_head[key]["matches"][match_id]
    
    # Handle dismissal separately (always increment)
    if is_dismissal:
        match_stats["dismissals"] += 1
        print(f"[H2H] Incrementing dismissal for {key} in match {match_id}")
    
    # Update runs and balls based on append mode
    if append:
        match_stats["runs"] += runs
        match_stats["balls"] += balls
        print(f"[H2H] Adding {runs} runs, {balls} balls for {key} in match {match_id}")
    else:
        match_stats["runs"] = runs
        match_stats["balls"] = balls
        print(f"[H2H] Setting {runs} runs, {balls} balls for {key} in match {match_id}")
    
    # Recalculate totals across all matches
    total_runs = 0
    total_balls = 0
    total_dismissals = 0
    
    for m_id, stats in head_to_head[key]["matches"].items():
        total_runs += stats["runs"]
        total_balls += stats["balls"]
        total_dismissals += stats["dismissals"]
    
    # Update the aggregated stats
    head_to_head[key]["runs"] = total_runs
    head_to_head[key]["balls"] = total_balls
    head_to_head[key]["dismissals"] = total_dismissals
    
    # Print summary for debugging
    print(f"[H2H] Updated totals for {key}: {total_runs} runs, {total_balls} balls, {total_dismissals} dismissals")
    
    # Save to disk
    with open(HEAD_TO_HEAD_FILE, "w") as f:
        json.dump(head_to_head, f, indent=4)
    
    return head_to_head[key]

# Helper to safely convert to int
def safe_int(val):
    try:
        return int(float(val))
    except Exception:
        return 0

# Helper to clean field names for robust matching
def clean_field_name(name):
    # Remove backticks, asterisks, and extra spaces, and lowercase
    return name.replace('`', '').replace('*', '').strip().lower()

# Add a function to clean player names
def clean_player_name(name):
    return name.replace('*', '').replace('`', '').replace('-', '').strip()

# Modify canonical_player_name to always return a name (never None)
def canonical_player_name(name, player_stats):
    # Remove trailing numbers and extra spaces
    name = regex.sub(r'\s*\d+\s*$', '', name).strip()
    # Try exact match (case-insensitive)
    for player in player_stats:
        if player.lower() == name.lower():
            return player
    # Try startswith match (case-insensitive)
    for player in player_stats:
        if player.lower().startswith(name.lower()):
            return player
    # Try fuzzy substring match (case-insensitive)
    for player in player_stats:
        if name.lower() in player.lower() or player.lower() in name.lower():
            return player
    # Fallback: return the cleaned name
    return name

# Helper to extract the best-matching player name from a line
# (tries to match against players.json, else falls back to original logic)
def extract_player_name_from_line(line, player_stats):
    parts = line.split()
    # Try to match against all names in players.json
    for player in player_stats:
        if player.lower() in line.lower():
            return player
    # Fallback: use all but last 3 columns
    if len(parts) > 3:
        return clean_player_name(" ".join(parts[:-3]))
    return clean_player_name(" ".join(parts))

# Update on_message to process both batters and bowlers sections independently and robustly
@bot.event
async def on_message(message):
    global head_to_head, player_stats, prev_striker
    striker = None
    non_striker = None
    bowler = None

    # Reload player_stats at the start of each message
    try:
        with open(PLAYERS_FILE, "r") as f:
            player_stats = json.load(f)
    except Exception as e:
        print(f"Error loading player_stats: {e}")
        if not player_stats:  # Only initialize if empty
            player_stats = {}

    # Only process messages from Cricket Guru bot
    CG_BOT_ID = 814100764787081217
    if message.author.bot and message.embeds and message.author.id == CG_BOT_ID:
        match_id = None
        for match in active_matches:
            if match.get("channel_id") == message.channel.id:
                match_id = match["match_id"]
                break
        if not match_id:
            return  # No active match in this channel

        try:
            embed = message.embeds[0]
            # Extract data from the embed
            
            # Process batters section
            batters_found = False
            for field in embed.fields:
                if field.name == "BATTERS":
                    batters_found = True
                    # Get the lines from the batters section
                    lines = field.value.strip().split('\n')
                    
                    # Skip processing if there are no valid lines
                    if len(lines) < 1:
                        continue
                    
                    # Process each batter line (skip header row if needed)
                    for line in lines:
                        # Regex to extract name and stats - adjust as needed based on your format
                        # Format is typically: Name R B SR
                        parts = line.split()
                        
                        # Need at least 3 parts for name, runs, balls
                        if len(parts) >= 3:
                            # The last 3 elements should be R, B, SR
                            try:
                                # Get the last 3 elements
                                r_index = -3
                                b_index = -2
                                
                                # Extract runs and balls
                                runs = int(parts[r_index])
                                balls = int(parts[b_index])
                                
                                # Everything before the last 3 elements is the name
                                name = " ".join(parts[:r_index])
                                
                                # Clean the player name
                                name = clean_player_name(name)
                                
                                # Update player stats
                                update_stats(name, runs=runs, balls=balls, match_id=match_id, bowler=bowler, is_dismissal=False)

                            except (ValueError, IndexError) as e:
                                print(f"Error parsing batter stats: {line} - {str(e)}")
                                continue
            
            # Process bowler section
            for field in embed.fields:
                if field.name == "BOWLER":
                    # Get the lines from the bowler section
                    lines = field.value.strip().split('\n')
                    
                    # Skip processing if there are no valid lines
                    if len(lines) < 1:
                        continue
                    
                    # Process each bowler line
                    for line in lines:
                        # Format is typically: Name O R W
                        parts = line.split()
                        
                        # Need at least 4 parts for a valid entry
                        if len(parts) >= 4:
                            try:
                                # The last 3 elements should be O, R, W
                                o_index = -3
                                r_index = -2
                                w_index = -1
                                
                                # Extract overs, runs, wickets
                                overs_str = parts[o_index]
                                runs_conceded = int(parts[r_index])  # These are runs CONCEDED, not scored
                                wickets = int(parts[w_index])
                                
                                # Convert overs to balls (1 over = 6 balls)
                                if "." in overs_str:
                                    main_overs, partial_balls = overs_str.split(".")
                                    balls = int(main_overs) * 6 + int(partial_balls)
                                else:
                                    balls = int(float(overs_str)) * 6
                                
                                # Everything before the last 3 elements is the name
                                name = " ".join(parts[:o_index])
                                
                                # Clean the player name
                                name = clean_player_name(name)
                                
                                # Update player stats - FIX: runs=0, runs_conceded=runs_conceded
                                update_stats(name, runs=0, wickets=wickets, balls=balls, match_id=match_id, runs_conceded=runs_conceded)

                            except (ValueError, IndexError) as e:
                                print(f"Error parsing bowler stats: {line} - {str(e)}")
                                continue
            
            # Process each field in case the embed has a different structure
            if not batters_found:
                for field in embed.fields:
                    # Check if field looks like it contains batting stats
                    if any(keyword in field.name.lower() for keyword in ["batter", "batting", "batsmen"]):
                        lines = field.value.strip().split('\n')
                        
                        # Skip header if it exists
                        start_idx = 1 if len(lines) > 1 and any(x in lines[0].lower() for x in ["name", "player", "batsman"]) else 0
                        
                        for line in lines[start_idx:]:
                            parts = line.strip().split()
                            if len(parts) >= 3:
                                try:
                                    # Try to identify which columns are runs and balls
                                    # Look for numeric values
                                    numeric_indices = [i for i, p in enumerate(parts) if p.replace(".", "").isdigit()]
                                    
                                    if len(numeric_indices) >= 2:
                                        name = " ".join(parts[:numeric_indices[0]]).strip()
                                        runs = int(float(parts[numeric_indices[0]]))
                                        balls = int(float(parts[numeric_indices[1]]))
                                        
                                        # Clean the player name
                                        name = clean_player_name(name)
                                        
                                        update_stats(name, runs=runs, balls=balls, match_id=match_id, bowler=bowler, is_dismissal=False)

                                except (ValueError, IndexError) as e:
                                    print(f"Error parsing batter stats (alt format): {line} - {str(e)}")
                    
                    # Check if field looks like it contains bowling stats
                    elif any(keyword in field.name.lower() for keyword in ["bowler", "bowling"]):
                        lines = field.value.strip().split('\n')
                        
                        # Skip header if it exists
                        start_idx = 1 if len(lines) > 1 and any(x in lines[0].lower() for x in ["name", "player", "bowler", "over"]) else 0
                        
                        for line in lines[start_idx:]:
                            parts = line.strip().split()
                            if len(parts) >= 3:
                                try:
                                    # Find numeric values for bowling stats
                                    numeric_indices = [i for i, p in enumerate(parts) if p.replace(".", "").isdigit()]
                                    
                                    if len(numeric_indices) >= 3:
                                        name = " ".join(parts[:numeric_indices[0]]).strip()
                                        overs_str = parts[numeric_indices[0]]
                                        runs_conceded = int(float(parts[numeric_indices[1]]))  # FIX: These are runs conceded
                                        wickets = int(float(parts[numeric_indices[2]]))
                                        
                                        # Clean the player name
                                        name = clean_player_name(name)
                                        
                                        # Convert overs to balls
                                        if "." in overs_str:
                                            main_overs, partial_balls = overs_str.split(".")
                                            balls = int(main_overs) * 6 + int(partial_balls)
                                        else:
                                            balls = int(float(overs_str)) * 6
                                        
                                        # FIX: runs=0, runs_conceded=runs_conceded
                                        update_stats(name, runs=0, wickets=wickets, balls=balls, match_id=match_id, runs_conceded=runs_conceded)

                                except (ValueError, IndexError) as e:
                                    print(f"Error parsing bowler stats (alt format): {line} - {str(e)}")
                                    
             # --- IMPROVED Timeline parsing and head-to-head update logic ---
            try:
                # Extract current striker, non-striker, and bowler from the embed
                is_last_ball_of_match = False
                if "won" in embed.description.lower() if embed.description else False:
                    is_last_ball_of_match = True
                    print("Detected last ball of match - found 'won' in embed description")
                elif "won" in embed.title.lower() if embed.title else False:
                    is_last_ball_of_match = True
                    print("Detected last ball of match - found 'won' in embed title")
                else:
                    for field in embed.fields:
                        if "won" in field.value.lower():
                            is_last_ball_of_match = True
                            print(f"Detected last ball of match - found 'won' in field: {field.name}")
                            break
                
                for field in embed.fields:
                    cleaned_field_name = clean_field_name(field.name)
                    if "batters" in cleaned_field_name:
                        lines = field.value.strip().split('\n')
                        if len(lines) >= 2:
                            striker_line = lines[0].split()
                            non_striker_line = lines[1].split()
                            
                            # Extract names by removing the last 3 elements (R B SR)
                            striker = clean_player_name(" ".join(striker_line[:-3]))
                            non_striker = clean_player_name(" ".join(non_striker_line[:-3]))
                            
                    elif "bowler" in cleaned_field_name:
                        lines = field.value.strip().split('\n')
                        if lines:
                            bowler_line = lines[0].split()
                            # Extract name by removing the last 3 elements (O R W)
                            # Also remove any over numbers that might be appended
                            bowler = clean_player_name(" ".join(bowler_line[:-3]))
                            # Remove any over numbers that might be at the end
                            bowler = regex.sub(r'\s+\d+\.\d+$', '', bowler)

                # Get canonical names if available, with None checks
                striker_canon = None
                non_striker_canon = None
                bowler_canon = None

                if striker is not None:
                    striker_canon = canonical_player_name(striker, player_stats) or striker
                if non_striker is not None:
                    non_striker_canon = canonical_player_name(non_striker, player_stats) or non_striker
                if bowler is not None:
                    bowler_canon = canonical_player_name(bowler, player_stats) or bowler
                
                # Now process the timeline if we have all needed players
                if striker_canon and bowler_canon and match_id:
                    for field in embed.fields:
                        if "timeline" in clean_field_name(field.name):
                            timeline = field.value.strip().split()
                            if not timeline:
                                continue
                                
                            # Get the rightmost entry
                            latest = timeline[-1].replace(":", "").lower()
                            is_last_ball = False

                            if latest == '|' and len(timeline) > 1:
                                latest = timeline[-2].replace(":", "").lower()
                                is_last_ball = True

                            print(f"Processing timeline entry: {latest} (is_last_ball: {is_last_ball}, is_last_ball_of_match: {is_last_ball_of_match})")

                            state = match_state.setdefault(match_id, {
                                "prev_striker": None,
                                "current_striker": None,
                                "current_non_striker": None,
                            })
                            # Use state["prev_striker"], state["current_striker"], state["current_non_striker"]

                            state["current_striker"] = striker_canon
                            state["current_non_striker"] = non_striker_canon

                            # Handle 0runs
                            if latest.startswith("<0runs"):
                                state["prev_striker"] = state["current_striker"]
                                if is_last_ball and state["current_non_striker"] is not None:
                                    state["current_striker"], state["current_non_striker"] = state["current_non_striker"], state["current_striker"]
                                    state["prev_striker"] = state["current_non_striker"]
                                update_head_to_head(state["current_striker"], bowler_canon, 0, 1, match_id, is_dismissal=False, append=True)
                                print(f"Updated H2H: {state['current_striker']} vs {bowler_canon} - added 0 runs, 1 ball")
                                

                            run_match = regex.search(r'([1-6])run', latest)
                            if run_match:
                                runs = int(run_match.group(1))
                                state["prev_striker"] = state["current_striker"]
                                # Last ball: swap for 2,4,6,0; don't swap for 1,3
                                if is_last_ball and not is_last_ball_of_match:
                                    if runs in [2, 4, 6] and state["current_non_striker"] is not None:
                                        state["current_striker"], state["current_non_striker"] = state["current_non_striker"], state["current_striker"]
                                        state["prev_striker"] = state["current_non_striker"]
                                elif  is_last_ball_of_match:
                                    if runs in [1,3] and state["current_non_striker"] is not None:
                                        state["current_striker"], state["current_non_striker"] = state["current_non_striker"], state["current_striker"]
                                        state["prev_striker"] = state["current_non_striker"]
                                # Other balls: swap for 1,3; don't swap for 2,4,6,0
                                else:
                                    if runs in [1, 3] and state["current_non_striker"] is not None:
                                        state["current_striker"], state["current_non_striker"] = state["current_non_striker"], state["current_striker"]
                                        state["prev_striker"] = state["current_non_striker"]
                                
                                update_head_to_head(state["current_striker"], bowler_canon, runs, 1, match_id, is_dismissal=False, append=True)
                                print(f"Updated H2H: {state['current_striker']} vs {bowler_canon} - added {runs} runs")
                                


                            elif 'w' in latest or 'wicket' in latest:
                                if state["prev_striker"] is not None:
                                    prev_striker_canon = canonical_player_name(state["prev_striker"], player_stats) or state["prev_striker"]
                                    update_head_to_head(prev_striker_canon, bowler_canon, 0, 1, match_id, is_dismissal=True, append=True)
                                    print(f"Updated H2H: {prev_striker_canon} vs {bowler_canon} - added dismissal")
                                    
                                    # Find the new striker (replacing prev_striker)
                                    for f in embed.fields:
                                        if "batters" in clean_field_name(f.name):
                                            batter_lines = f.value.strip().split('\n')
                                            for line in batter_lines:
                                                parts = line.split()
                                                if len(parts) >= 3:
                                                    candidate = clean_player_name(" ".join(parts[:-3]))
                                                    candidate_canon = canonical_player_name(candidate, player_stats) or candidate
                                                    # If this candidate is not the previous striker or non-striker, they must be the new striker
                                                    if candidate_canon not in [state["prev_striker"], state["current_non_striker"]]:
                                                        striker_canon = candidate_canon
                                                        state["current_striker"] = striker_canon
                                                        # For last ball of over, new batter comes in at non-striker's end
                                                        if is_last_ball:
                                                            state["current_non_striker"] = striker_canon
                                                            state["current_striker"] = state["current_non_striker"]
                                                        state["prev_striker"] = state["current_striker"]  # Update prev_striker to the new striker
                                                        break
                                else:
                                    print(f"WARNING: Could not record dismissal - prev_striker is None")

                            # Handle extras and other special cases
                            elif any(x in latest for x in ["wd", "nb", "wide", "noball", "bye", "legbye"]):
                                # Log extras but don't count as balls faced or update prev_striker
                                state["prev_striker"] = state["current_striker"]
                                print(f"Detected extras: {latest} - not updating head-to-head or prev_striker")
                            # Handle any other unrecognized entries (like "|")
                            else:
                                print(f"Ignoring unrecognized timeline entry: {latest}")
                                state["prev_striker"] = state["current_striker"]
                
            except Exception as e:
                print(f"[Timeline Parser Error] {e}")
                import traceback
                traceback.print_exc()

        except Exception as e:
            print(f"Error processing embed: {str(e)}")
    
    # Process commands
    await bot.process_commands(message)
    
  

# Add leaderboard command
@bot.command(aliases=["lb"])
async def leaderboard(ctx):
    generate_leaderboard_image()
    with open("leaderboard.png", "rb") as file:
        await ctx.send(file=discord.File(file, "leaderboard.png"))


# Add stats command
@bot.command(aliases=["player"])
async def stats(ctx, *, player: str):
    with open(PLAYERS_FILE, "r") as f:
        stats = json.load(f)

    data = stats.get(player)
    if data:
        await ctx.send(f"📈 **{player}** → {data['runs']} runs, {data['balls']} balls, {data['wickets']} wickets")
    else:
        await ctx.send(f"❌ No data found for **{player}**")

# Add match tracking commands
@bot.command(aliases=["start"])
async def startmatch(ctx):
    """Start tracking a new match."""
    global match_counter
    match_counter += 1
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    match_id = f"Match_{timestamp}_{match_counter}"
    
    channel_id = ctx.channel.id
    active_matches.append({
        "match_id": match_id,
        "channel_id": channel_id,
        "start_time": str(datetime.datetime.now()),
        "status": "in_progress"
    })
    match_state[match_id] = {
        "prev_striker": None,
        "current_striker": None,
        "current_non_striker": None,
    }
    save_data()

    embed = discord.Embed(title="🏏 Match Started", color=discord.Color.green())
    embed.add_field(name="Match ID", value=match_id, inline=False)
    embed.add_field(name="Status", value="Match is now being tracked.", inline=False)
    embed.add_field(name="Started", value=active_matches[-1]["start_time"], inline=False)
    await ctx.send(embed=embed)

@bot.command(aliases=["end"])
async def endmatch(ctx, match_id: str = None):
    """End tracking a match."""
    if not active_matches:
        await ctx.send("❌ No active matches to end!")
        return

    if match_id is None:
        # End the most recent match if no match_id provided
        match = active_matches.pop()
        match_id = match["match_id"]
    else:
        # Find and remove the specified match
        for i, match in enumerate(active_matches):
            if match["match_id"] == match_id:
                match = active_matches.pop(i)
                break
        else:
            await ctx.send(f"❌ Match {match_id} not found in active matches!")
            return

    save_data()

    embed = discord.Embed(title="🏏 Match Ended", color=discord.Color.blue())
    embed.add_field(name="Match ID", value=match_id, inline=False)
    embed.add_field(name="Status", value="Match tracking ended.", inline=False)
    embed.add_field(name="Duration", value=f"Started at {match['start_time']}", inline=False)
    await ctx.send(embed=embed)

    if match_id in match_state:
        del match_state[match_id]

@bot.command(aliases=["status"])
async def matchstatus(ctx):
    """Show all active matches."""
    if not active_matches:
        await ctx.send("No active matches at the moment.")
        return

    embed = discord.Embed(title="🏏 Active Matches", color=discord.Color.gold())
    for match in active_matches:
        embed.add_field(
            name=match["match_id"],
            value=f"Started: {match['start_time']}\nStatus: {match['status']}",
            inline=False
        )
    await ctx.send(embed=embed)
@bot.command(aliases=["topbat"])
async def top_batters(ctx, sortby: str = "runs"):
    with open(PLAYERS_FILE, "r") as f:
        stats = json.load(f)

    with open("player_team_map.json", "r") as f:
        player_teams = json.load(f)

    batters = []
    for name, data in stats.items():
        runs = data.get("runs", 0)
        balls = data.get("balls", 0)
        sr = (runs / balls * 100) if balls > 0 else 0
        batters.append((name, runs, sr))

    if sortby == "sr":
        batters.sort(key=lambda x: (-x[2], -x[1]))
    else:
        batters.sort(key=lambda x: (-x[1], -x[2]))

    top_batters = batters[:10]
    create_player_list_image(top_batters, "Top Batters", sortby, "top_batters.png", player_teams, is_bowler=False)
    with open("top_batters.png", "rb") as file:
        await ctx.send(file=discord.File(file, "top_batters.png"))

@bot.command(aliases=["topbowl"])
async def top_bowlers(ctx, sortby: str = "wickets"):
    with open(PLAYERS_FILE, "r") as f:
        stats = json.load(f)

    with open("player_team_map.json", "r") as f:
        player_teams = json.load(f)

    bowlers = []
    for name, data in stats.items():
        wickets = data.get("wickets", 0)
        balls = data.get("balls", 0)
        runs_conceded = data.get("runs_conceded", 0)
        overs = balls / 6 if balls else 0
        economy = (runs_conceded / overs) if overs > 0 else 0
        bowlers.append((name, wickets, economy))

    if sortby == "eco":
        bowlers.sort(key=lambda x: (x[2], -x[1]))
    else:
        bowlers.sort(key=lambda x: (-x[1], x[2]))

    top_bowlers = bowlers[:10]
    create_player_list_image(top_bowlers, "Top Bowlers", sortby, "top_bowlers.png", player_teams, is_bowler=True)
    with open("top_bowlers.png", "rb") as file:
        await ctx.send(file=discord.File(file, "top_bowlers.png"))

def create_player_list_image(data, title, sortby, filename, player_teams, is_bowler=False):
    from PIL import ImageOps

    width, height = 900, 800
    image = Image.new("RGB", (width, height), (20, 20, 20))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 22)
    title_font = ImageFont.truetype("arial.ttf", 30)

    draw.text((width//2 - 200, 20), f"🏆 {title} (sorted by {sortby})", fill=(255, 215, 0), font=title_font)

    y = 80
    for i, (name, val1, val2) in enumerate(data):
        avatar_path = f"assets/avatars/{name}.png"
        if not os.path.exists(avatar_path):
            avatar_path = f"assets/avatars/{name}.jpg"
        if os.path.exists(avatar_path):
            avatar = Image.open(avatar_path).convert("RGBA")
            avatar = avatar.resize((50, 50))
            avatar = ImageOps.fit(avatar, (50, 50), centering=(0.5, 0.5))
            image.paste(avatar, (60, y), avatar)

        team_code = player_teams.get(name, "")
        logo_path = f"assets/logos/{team_code}.png"
        if os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((40, 40))
            image.paste(logo, (120, y + 5), logo)

        draw.text((180, y + 10), f"{i+1}. {name}", fill=(255, 255, 255), font=font)
        stat_text = f"{val1} runs, SR: {val2:.2f}" if not is_bowler else f"{val1} wickets, Econ: {val2:.2f}"
        draw.text((550, y + 10), stat_text, fill=(200, 200, 200), font=font)
        y += 60

    image.save(filename)

@bot.command(aliases=["mp"])
async def mapplayer(ctx, *, input: str):
    """
    Map a player to a team.
    Usage: !mapplayer <player name> -> <team code>
    """
    try:
        if "->" not in input:
            await ctx.send("❌ Use `->` to map: Example: `!mapplayer Virat Kohli -> VLA`")
            return

        player_name, team_code = map(str.strip, input.split("->", 1))

        if os.path.exists("player_team_map.json"):
            with open("player_team_map.json", "r") as f:
                mapping = json.load(f)
        else:
            mapping = {}

        mapping[player_name] = team_code.upper()

        with open("player_team_map.json", "w") as f:
            json.dump(mapping, f, indent=4)

        embed = discord.Embed(title="✅ Player Mapped",
                              description=f"**{player_name}** mapped to team **{team_code.upper()}**.",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")



# Helper function for 3-letter case-insensitive prefix matching
def find_h2h_player(prefix, all_names):
    prefix = prefix.lower()
    for name in all_names:
        if name.lower().startswith(prefix):
            return name
    return None

# Add head-to-head command
@bot.command(aliases=["h2h"])
async def headtohead(ctx, batter: str, bowler: str):
    global head_to_head
    
    # Load player stats for canonical name lookup
    with open(PLAYERS_FILE, "r") as f:
        player_stats = json.load(f)
    
    # Try to find the canonical names
    batter_name = canonical_player_name(batter, player_stats)
    bowler_name = canonical_player_name(bowler, player_stats)
    
    # Get exact key match
    key = f"{batter_name} vs {bowler_name}"
    if key in head_to_head:
        data = head_to_head[key]
        sr = (data['runs'] / data['balls'] * 100) if data['balls'] > 0 else 0.0
        await ctx.send(
            f"📊 **{batter_name} vs {bowler_name}**\n"
            f"Runs: {data['runs']} | Balls: {data['balls']} | "
            f"Dismissals: {data['dismissals']} | SR: {sr:.2f}"
        )
        return
    
    # If no exact match, try to find a key that contains the names
    for k in head_to_head.keys():
        parts = k.split(" vs ")
        if len(parts) != 2:
            continue
        
        k_batter, k_bowler = parts
        if (batter.lower() in k_batter.lower() and bowler.lower() in k_bowler.lower()):
            data = head_to_head[k]
            sr = (data['runs'] / data['balls'] * 100) if data['balls'] > 0 else 0.0
            await ctx.send(
                f"📊 **{k_batter} vs {k_bowler}**\n"
                f"Runs: {data['runs']} | Balls: {data['balls']} | "
                f"Dismissals: {data['dismissals']} | SR: {sr:.2f}"
            )
            return
    
    await ctx.send(f"No head-to-head data found for **{batter_name} vs {bowler_name}**.")

# Run the bot
bot.run('MTMyNjA3NzMxMzgxNjk4OTc3Ng.Gz1kYO.WFmB6gbb-zsUE-pa8y9SCwauCqL5lKY3mi4gvM')