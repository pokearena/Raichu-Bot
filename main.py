import asyncio
import json
import random
import re
import time
import zoneinfo
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord.ui import View

from dotenv import GUILD_ID, ALLY_role, TOKEN


intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or("%"), strip_after_prefix=True, case_insensitive=True,
                   intents=intents)
bot.activity = discord.Activity(type=discord.ActivityType.playing, name="🌊Sugar Surf!🌸")

INFINITY_role = 1102473662352863242
IMMORTAL_role = 1102473551195410502
VOID_role = 1102473472438972448


clan_role_set = {INFINITY_role, IMMORTAL_role, VOID_role}
clan_channels = {INFINITY_role: 1123818520002711622, IMMORTAL_role: 1123815087350763520, VOID_role: 1123814492309041253}
clan_emotes = {INFINITY_role: "<a:infinity:1118053955314921472>",  IMMORTAL_role: "<a:immortal:1118053951791697930>", VOID_role: "<a:void:1118053970913538068>"}
clan_welcome_texts = ["Hey hey {mention}!! ⚡", "🤺 Engarde!! {mention}", "⚔️{mention} barged in.."]


# Sorted list of timezones
timezones = [tz[0] for tz in sorted([(tz, datetime.now(zoneinfo.ZoneInfo(tz)).utcoffset()) for tz in zoneinfo.available_timezones()], key=lambda x: x[1])]


def generate_all_tz_embeds():
    # uses datetime.now() so should be freshly generated
    return [discord.Embed(
        color=discord.Color.gold(), title="Available Timezones",
        description="\n".join([f"- {tz} ▪ {datetime.now(zoneinfo.ZoneInfo(tz)).strftime('%A, %I:%M %p')}" for tz in timezones[i*100:(i+1)*100]]))
        for i in range((len(timezones) - 1) // 100 + 1)]


# use as an okayish in-memory db
"""
// database.json
{
    "user_id": {"timezone": "tz", "enabled": true/false]
}
"""
with open("database.json", "r") as fp:
    data = json.load(fp)


def update_db():
    with open("database.json", "w") as f:
        json.dump(data, f, indent=4)


class AllTimezonePaginator(View):
    def __init__(self, embeds):
        self.current_page = 0
        self.pages = (len(timezones) - 1) // 100
        self.embeds = embeds
        super().__init__(timeout=120)

    @discord.ui.button(emoji="◀️")
    async def left_button(self, interaction, btn):
        if self.current_page == 0:
            self.current_page = self.pages
        else:
            self.current_page -= 1
        emb = self.embeds[self.current_page]
        self.children[1].label = f"Page {self.current_page + 1} / {self.pages + 1}"
        await interaction.response.edit_message(view=self, embed=emb)

    @discord.ui.button(label=f"Page 1/{(len(timezones) - 1) // 100 + 1}", style=discord.ButtonStyle.blurple, disabled=True)
    async def page_label_button(self, interaction, btn):
        """This button is a display-only button to show Pages"""

    @discord.ui.button(emoji="▶️")
    async def right_button(self, interaction, btn):
        if self.current_page == self.pages:
            self.current_page = 0
        else:
            self.current_page += 1
        emb = self.embeds[self.current_page]
        self.children[1].label = f"Page {self.current_page + 1} / {self.pages + 1}"

        await interaction.response.edit_message(view=self, embed=emb)


@bot.event
async def on_ready():
    print("Raichu Bot is online!")


# Clan Welcome Feature
async def clan_welcome(member, clan_role_id):
    clan_role = member.guild.get_role(clan_role_id)
    member_count = len([m for m in member.guild.members if clan_role in m.roles])
    emb = discord.Embed(color=clan_role.color, title="🔔 New Clan Member")
    emb.description = f"A new member has joined our {clan_role.mention}!\nDo welcome {member.display_name} aboard!"
    emb.set_footer(
        text=f"{clan_role.name[5:]} now has {member_count} members.")  # skips out 'Team '  from Team Infinity, Team Immortal and Team Void
    emb.set_image(url=member.avatar)
    clan_channel = member.guild.get_channel(clan_channels[clan_role.id])
    m = await clan_channel.send(content=random.choice(clan_welcome_texts).format(mention=member.mention), embed=emb)
    await m.add_reaction(clan_emotes[clan_role.id])


@bot.event
async def on_member_update(before_m, after_m):
    """Clan join notification"""
    if after_m.bot:
        return

    before = {role.id for role in before_m.roles}
    if clan_role_set.intersection(before):
        return
    after = {role.id for role in after_m.roles}
    clan_role = clan_role_set.intersection(after)
    if clan_role:
        await clan_welcome(after_m, clan_role.pop())


small_timeout_map = dict()
site_regex = re.compile(r'((?:^| )(?:http://|https://|)(?:www\.|)pokearena.xyz(?: |$))')
vanity_regex = re.compile(r'((?:^| )(?:\.gg|discord\.gg)/pokearena(?: |$))')


def contains_vanity(status_content: str):
    guild = bot.get_guild(GUILD_ID)
    if guild.premium_tier == 3:
        return vanity_regex.findall(status_content) or site_regex.findall(status_content)
    return site_regex.findall(status_content)


async def greenlist_vanity_emb(member: discord.Member):
    """
    Called when a member is provided vanity role
    To send a dm/modify sent dm
    """
    channel = member.dm_channel
    if channel is None:
        try:
            channel = await member.create_dm()
        except:
            return  # not possible
    # Check channel history upto 20 msges
    async for message in channel.history(limit=20):
        if message.author != member and message.embeds and message.embeds[0].title == "⭐ New Ally":
            emb = message.embeds[0]
            # For old dms, where no field was sent
            if not emb.fields:
                emb.add_field(name="Last Updated:", value=discord.utils.format_dt(datetime.now(), "R"))
                emb.add_field(name="Action Done:", value="✅ Added **Ally** role to you")
            else:
                emb.set_field_at(0, name=emb.fields[0].name, value=discord.utils.format_dt(datetime.now(), "R"))
                emb.set_field_at(1, name=emb.fields[1].name, value="✅ Added **Ally** role to you")
            await message.edit(embed=emb)
            break
    else:
        emb = discord.Embed(color=discord.Color.gold(), title='⭐ New Ally')
        emb.description = f"<:like:1118127706928857149> Hey **{member.name.title()}**, it is commendable that you have" \
                          " supported Pokearena Official! You are now an **Ally** of arena as our token of gratitude! 🌠"
        emb.set_thumbnail(
            url="https://cdn.discordapp.com/icons/1006542206569558116/583fa7c3571c84397ce5c4577cb6df63.png?size=1024")
        emb.add_field(name="Last Updated:", value=discord.utils.format_dt(datetime.now(), "R"))
        emb.add_field(name="Action Done:", value="✅ Added **Ally** role to you")
        await channel.send(embed=emb)


async def redlist_vanity_emb(member: discord.Member):
    """
    Called when a member is removed from vanity role
    To modify sent dm if applicable
    """
    channel = member.dm_channel
    if channel is None:
        try:
            channel = await member.create_dm()
        except:
            return  # not possible
    # Check channel history upto 20 msges
    async for message in channel.history(limit=20):
        if message.author != member and message.embeds and message.embeds[0].title == "⭐ New Ally":
            emb = message.embeds[0]
            if not emb.fields:
                emb.add_field(name="Last Updated:", value=discord.utils.format_dt(datetime.now(), "R"))
                emb.add_field(name="Action Done:", value="❌ Removed **Ally** role from you")
            else:
                emb.set_field_at(0, name=emb.fields[0].name, value=discord.utils.format_dt(datetime.now(), "R"))
                emb.set_field_at(1, name=emb.fields[1].name, value="❌ Removed **Ally** role from you")
            return await message.edit(embed=emb)


async def clear_vanity_oncheck(member):
    if member.get_role(ALLY_role) is not None:
        if member.raw_status == "offline":
            await member.remove_roles(member.guild.get_role(ALLY_role))
            small_timeout_map[member.id] = int(time.time()) + 30  # 30 seconds cooldown
            await redlist_vanity_emb(member)
            return True
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity) and contains_vanity(str(activity.name)):
                break
        else:
            await member.remove_roles(member.guild.get_role(ALLY_role))
            small_timeout_map[member.id] = int(time.time()) + 30  # 30 seconds cooldown
            await redlist_vanity_emb(member)
            return True


@bot.command()
@commands.is_owner()
async def fix_vanity(ctx):
    # to run when bot is rebooted
    count = 0
    for member in ctx.guild.members:
        if await clear_vanity_oncheck(member):
            count += 1
    await ctx.send(f'Fixed from {count} members.')


@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send('Successfully synced!')


@bot.hybrid_command(aliases=('flip', ))
@commands.cooldown(1, 2.0, commands.BucketType.user)
async def coinflip(ctx):
    """%flip, a simple coin flip"""
    await ctx.send(f"{ctx.author.mention} {random.choice(['heads', 'tails', 'heads', 'tails'])}", allowed_mentions=discord.AllowedMentions(users=False))  # for no particular reason


@bot.hybrid_command(aliases=('vanity', ))
@commands.cooldown(1, 2.0, commands.BucketType.channel)
async def ally(ctx):
    """%ally, info on obtaining vanity role"""
    emb = discord.Embed(color=discord.Color.blurple())
    emb.title = "🔥 Arena Rewards!"
    availability = "" if ctx.guild.premium_tier == 3 else "❌ discord.gg/pokearena is unavailable until Server reaches level 3 -> see %boost"
    emb.description = f"""
╔⏤‧˚❀༉.⏤╝❀╚⏤⏤⏤⏤╗
Time limited <@&{ALLY_role}> role
╚⏤⏤⏤⏤╗❀╔⏤‧˚❀༉.⏤╝

💭 How to obtain?
`Ans:` **Add discord.gg/pokearena or pokearena.xyz into your 📝custom status** and our Helper {ctx.bot.user.mention} will give you the role, along with a thankyou note <:like:1118127706928857149> 

💖 The ally role is hoisted and will show off higher than level roles ✨ 
⚠️ It goes away if you take away the status/go offline
"""
    if availability:
        emb.set_footer(text=availability)
    await ctx.send(embed=emb)


@bot.hybrid_command(aliases=('boost', ))
@commands.guild_only()
@commands.cooldown(1, 3.0, commands.BucketType.channel)
async def boosters(ctx):
    """
    %boost, info of boosters
    """
    emb = discord.Embed(color=discord.Color.pink())
    if ctx.guild.premium_subscription_count:
        prem = ctx.guild.premium_subscribers
        emb.title = f"❤️‍🔥 {len(prem)} Arena Boosters | Level {ctx.guild.premium_tier} ({ctx.guild.premium_subscription_count} boosts) "
        emb.description = f"<:like:1118127706928857149> Thankful to all {ctx.guild.premium_subscriber_role.mention} of arena!\n- "
        emb.description += "\n- ".join([f"**{p}** ({p.mention})" for p in prem])
    else:
        emb.title = f"❤️‍🔥 Arena Boosters"
        emb.description = f"Boost now to support Pokearena Official and gain {ctx.guild.premium_subscriber_role.mention} role!"
    await ctx.send(embed=emb)

# Regex for 12h format time parsing
time_regex = re.compile(
    r'(?:^|\s)'
    r'(at|by|till|before|after)?'
    r'\s{0,3}(1[0-2]|0?[1-9])'
    r'\s{0,3}(?::\s{0,3}([0-5][0-9]))?'
    r'\s{0,3}(?:(am|pm).?)?'
    r'\s{0,2}(yesterday|tomorrow|day\s{0,3}after\s{0,3}tomorrow|day\s{0,3}before\s{0,3}yesterday)?'
    r'\s{0,3}(?:for\s{0,3}(<@!?[0-9]+>|[0-9]+|[a-z._]+))?'
    r'(?:\s|\?|\.|$)',
    re.IGNORECASE
)


async def parse_matchgroup_to_tz(context, message, match_group, embeds, embed_order):
    # Extract components
    _, hour, minute, am_pm, day_ref, user_mentioned = match_group

    tz = None
    if user_mentioned:  # for user
        try:
            member = await commands.MemberConverter().convert(context, user_mentioned)
        except commands.MemberNotFound:
            return
        else:
            if str(member.id) in data and data[str(member.id)]['enabled'] and data[str(member.id)]['timezone'] and message.guild.get_member(member.id):  # they need have a timezone
                tz = data[str(member.id)]['timezone']
                if member.id not in embed_order:
                    embeds[len(embed_order)].set_author(name=f"{member.name}'s time", icon_url=member.display_avatar)
                    embed_order.append(member.id)
            else:
                return
    if not tz:
        member = message.author
        tz = data.get(str(member.id), {}).get('timezone')
        if member.id not in embed_order:
            embeds[len(embed_order)].set_author(name=member.name, icon_url=member.display_avatar)
            embed_order.append(member.id)
        if not tz or not data[str(member.id)]['enabled']:
            return

    # Convert to 24-hour format
    hour = int(hour)
    if minute:
        minute = int(minute)
    else:
        minute = 0

    if am_pm:
        if am_pm.lower() == 'pm' and hour != 12:
            hour += 12
        elif am_pm.lower() == 'am' and hour == 12:
            hour = 0

    # Get current datetime in UTC
    now = datetime.now(zoneinfo.ZoneInfo(tz))

    # Adjust date based on day reference
    if day_ref:
        day_ref = day_ref.lower()
        if 'yesterday' in day_ref:
            now -= timedelta(days=1)
        elif 'tomorrow' in day_ref:
            now += timedelta(days=1)
        elif 'day after tomorrow' in day_ref:
            now += timedelta(days=2)
        elif 'day before yesterday' in day_ref:
            now -= timedelta(days=2)

    # Create the datetime object
    if not am_pm:
        result1 = now.replace(hour=hour + 12 if hour != 12 else 12, minute=minute)
        result2 = now.replace(hour=0 if hour == 12 else hour, minute=minute)
        return add_time_to_embed([result1, result2], embeds, embed_order, member)

    result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return add_time_to_embed([result], embeds, embed_order, member)


def add_time_to_embed(times, embeds, embed_order, member):
    for t in times:
        embeds[embed_order.index(member.id)].description += f'- {t.strftime("%I:%M %p") if t.minute else t.strftime("%I %p")} -> {discord.utils.format_dt(t, "F")} ({discord.utils.format_dt(t, "R")}) your time\n'


@bot.event
async def on_message(m):
    if m.author.bot:
        return

    # Find the first match
    matches = time_regex.findall(m.content)
    # prevent no match and lone hour matches
    matches = [match for match in matches if match[0] or any(match[2:-1])]
    if matches:
        # used to deal with complex chaining of sentences such as "12pm my time or 3pm for @person or 5pm for @anotherperson"
        embeds = [discord.Embed(color=discord.Color.dark_embed(), description=''),
                  discord.Embed(color=discord.Color.dark_embed(), description=''),
                  discord.Embed(color=discord.Color.dark_embed(), description='')]
        embed_order = []  # no members in order yet
        for match in matches[:3]:
            await parse_matchgroup_to_tz(await bot.get_context(m), m, match, embeds, embed_order)
        resultant_embs = [emb for emb in embeds if emb.description]
        if resultant_embs:
            await m.channel.send(embeds=resultant_embs)

    await bot.process_commands(m)


class TimezoneToggle(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Turn On", style=discord.ButtonStyle.green)
    async def callback(self, interaction, btn):
        if not data.get(str(interaction.user.id), {}).get('timezone'):
            return await interaction.response.send_message("You have not yet set a timezone, use %tz newtimezone or </timezone set:1257289655242719392>", ephemeral=True)
        await interaction.response.send_message('Turned ON live universal time response! Test it out by entering `11am` into the chat!', ephemeral=True)
        data[str(interaction.user.id)]['enabled'] = True
        update_db()


@bot.hybrid_group(
    name="timezone", description="Set your timezone for global times for everyone in chat",
    aliases=('tz', 'mytz', 'mytimezone'), fallback="set"
)
async def timezone(ctx, new_timezone=None):
    if new_timezone:
        if new_timezone not in timezones:
            embs = generate_all_tz_embeds()
            return await ctx.send('Unable to find mentioned timezone, please check in the following list to find your timezone:-\n**All shown timezones are sorted in ascending order for ease of finding your timezone!**', embed=embs[0], view=AllTimezonePaginator(embs), ephemeral=True)

        await ctx.send(f'Your timezone has now been set to `{new_timezone}`. Click below to get started! Use `%tz help` or </timezone help:1257289655242719392> to know more!!', view=TimezoneToggle())
        data[str(ctx.author.id)] = {'timezone': new_timezone, 'enabled': data.get(str(ctx.author.id), {}).get('enabled') or False}
        update_db()
    else:
        if str(ctx.author.id) not in data:
            return await ctx.send('You have not set any timezone yet for it to be reset. Use `%tz help` or </timezone help:1257289655242719392> to know more!!', ephemeral=True)

        await ctx.send('Successfully cleared your timezone. Set a new one via `%tz timezone` or </timezone set:1257289655242719392>', ephemeral=True)
        data[str(ctx.author.id)]['timezone'] = None
        update_db()


@timezone.autocomplete('new_timezone')
async def timezone_autocomplete(interaction, current: str):
    current = current.lower()
    return [discord.app_commands.Choice(name=tz, value=tz) for tz in timezones if current in tz.lower()][:20]


@timezone.command(name='help')
async def help_(ctx):
    """Guide for the timezone command"""
    emb = discord.Embed(color=discord.Color.brand_red(), title=f"🌐 Global Timezoner")
    emb.description = """
Engage in easy time conversations, where each time you mention is viewable by everyone in their own timezone. 
Simply specify your timezone in </timezone set:1257289655242719392> and enjoy the magic after turning it on via </timezone on:1257289655242719392>!
## Privacy Policy:
Raichu bot takes your privacy seriously.
Your timezone is private and no one can view it directly!
Raichu bot will never specify your timezone.
## Usage:
Usage involves specifying time in 12 hour format with am/pm
For example:-
- let's battle at 6pm my time
- does 11am suit you?
In-case you don't mention am/pm, the bot will show both times.

Additionally, you can use our smart syntax `<time> for <@member>`
to view global time according to someone else's time zone
For example:-
- let's battle when it is 8:15pm for @intenzi
- I want to know what time it is for me when it is 3am for @otherperson
Simply add `for @user` to any mentioned time, to view your time according to someone else's timezone
## Setup:
</timezone help:1257289655242719392>  -> shows this command
</timezone info:1257289655242719392>  -> view all available timezones
</timezone set:1257289655242719392> <new timezone>  -> setup your timezone
</timezone on:1257289655242719392>   -> turn on global time shower for your time based messages
</timezone off:1257289655242719392>  -> turn off global time shower for your time based messages
"""
    emb.set_footer(text="Built with ❤️ by Intenzi")
    await ctx.send(embed=emb)


@timezone.command(name='info')
async def information(ctx):
    """Show all available timezones"""
    embs = generate_all_tz_embeds()
    await ctx.send(content="All shown timezones are sorted in ascending order for ease of finding your timezone!", embed=embs[0], view=AllTimezonePaginator(embs))


@timezone.command()
async def on(ctx):
    """Start showing global time for times mentioned by you"""
    if not data.get(str(ctx.author.id), {}).get('timezone'):
        return await ctx.send("You have not yet set a timezone, use %tz newtimezone or </timezone set:1257289655242719392>")

    await ctx.send('Turned ON live universal time response! Test it out by entering `11am` into the chat!', ephemeral=True)
    data[str(ctx.author.id)]['enabled'] = True
    update_db()


@timezone.command()
async def off(ctx):
    """Stop showing global time for times mentioned by you"""
    if not data.get(str(ctx.author.id), {}).get('timezone'):
        return await ctx.send("You have not yet set a timezone, use %tz newtimezone or </timezone set:1257289655242719392>")

    await ctx.send('Turned OFF live universal time response!', ephemeral=True)
    data[str(ctx.author.id)]['enabled'] = False
    update_db()


@bot.event
async def on_member_join(member):
    """remove role from rejoiners that get it added back via carl sticky role"""
    if member.bot or member.guild.id != GUILD_ID:
        return

    await asyncio.sleep(2)
    await clear_vanity_oncheck(member)


@bot.event
async def on_presence_update(before_m, after_m):
    """vanity role"""
    if after_m.bot or after_m.guild.id != GUILD_ID:
        return

    # clear vanity in-case conditions are met
    if await clear_vanity_oncheck(after_m):
        return

    # add vanity in-case conditions are met
    for activity in after_m.activities:
        if isinstance(activity, discord.CustomActivity):
            if contains_vanity(str(activity.name)):
                if small_timeout_map.get(after_m.id, 0) > time.time():
                    return
                elif after_m.get_role(ALLY_role) is None:  # member does not have the ally role
                    role = after_m.guild.get_role(ALLY_role)
                    await after_m.add_roles(role)
                    small_timeout_map.pop(after_m.id, None)  # ignore errors
                    await greenlist_vanity_emb(after_m)
            return

bot.run(TOKEN)
