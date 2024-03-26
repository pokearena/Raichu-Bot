import asyncio
import random
import re
import time

import discord
from discord.ext import commands

from dotenv import TOKEN


intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or("%"), strip_after_prefix=True, case_insensitive=True,
                   intents=intents)
bot.activity = discord.Activity(type=discord.ActivityType.playing, name="🌊Sugar Surf!🌸")

GUILD_ID = 1006542206569558116
INFINITY_role = 1102473662352863242
IMMORTAL_role = 1102473551195410502
VOID_role = 1102473472438972448

ALLY_role = 1217377533155344435

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
vanity_regex = re.compile(r'((?:\.gg|discord\.gg)/pokearena(?: |$))')


async def clear_vanity_oncheck(member):
    if member.get_role(ALLY_role) is not None:
        if member.raw_status == "offline" or not vanity_regex.findall([a for a in member.activities if isinstance(a, discord.CustomActivity)][0].name):
            await member.remove_roles(member.guild.get_role(ALLY_role))
            small_timeout_map[member.id] = int(time.time()) + 30  # 30 seconds cooldown
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


@bot.event
async def on_member_join(member):
    """remove role from rejoiners that get it added back via carl sticky role"""
    if member.bot or member.guild.id != 1006542206569558116:
        return

    await asyncio.sleep(2)
    await clear_vanity_oncheck(member)


@bot.event
async def on_presence_update(before_m, after_m):
    """vanity role"""
    if after_m.bot or after_m.guild.id != 1006542206569558116:
        return

    # clear vanity in-case conditions are met
    if await clear_vanity_oncheck(after_m):
        return

    # add vanity in-case conditions are met
    for activity in after_m.activities:
        if isinstance(activity, discord.CustomActivity):
            match = vanity_regex.findall(str(activity.name))
            if match:
                if small_timeout_map.get(after_m.id, 0) > time.time():
                    return
                elif after_m.get_role(ALLY_role) is None:  # member does not have the ally role
                    role = after_m.guild.get_role(ALLY_role)
                    await after_m.add_roles(role)
                    small_timeout_map.pop(after_m.id, None)  # ignore errors
                    emb = discord.Embed(color=discord.Color.gold(), title='⭐ New Ally')
                    emb.description = f"<:like:1118127706928857149> Hey **{after_m.name.title()}**, it is commendable that you have" \
                                      " supported Pokearena Official! You are now an **Ally** of arena as our token of gratitude! 🌠"
                    emb.set_thumbnail(
                        url="https://cdn.discordapp.com/icons/1006542206569558116/583fa7c3571c84397ce5c4577cb6df63.png?size=1024")
                    try:
                        await after_m.send(embed=emb)
                    except:
                        pass
            return

bot.run(TOKEN)
