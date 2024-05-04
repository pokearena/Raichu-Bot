import asyncio
import random
import re
import time
from datetime import datetime

import discord
from discord.ext import commands

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
            if isinstance(activity, discord.CustomActivity) and contains_vanity(activity.name):
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
        emb.title = f"❤️‍🔥 {len(prem)} Arena Boosters ({ctx.guild.premium_subscription_count} boosts) | Level {ctx.guild.premium_tier}"
        emb.description = f"<:like:1118127706928857149> Thankful to all {ctx.guild.premium_subscriber_role.mention} of arena!"
        emb.description += "\n- ".join([f"**{p}** ({p.mention})" for p in prem])
    else:
        emb.title = f"❤️‍🔥 Arena Boosters"
        emb.description = f"Boost now to support Pokearena Official and gain {ctx.guild.premium_subscriber_role.mention} role!"
    await ctx.send(embed=emb)


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
            if contains_vanity(activity.name):
                if small_timeout_map.get(after_m.id, 0) > time.time():
                    return
                elif after_m.get_role(ALLY_role) is None:  # member does not have the ally role
                    role = after_m.guild.get_role(ALLY_role)
                    await after_m.add_roles(role)
                    small_timeout_map.pop(after_m.id, None)  # ignore errors
                    await greenlist_vanity_emb(after_m)
            return

bot.run(TOKEN)
