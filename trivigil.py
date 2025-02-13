import os
import discord
from discord.ext import commands
import aiohttp
import asyncio
import re
from typing import Dict
from datetime import datetime

class SearchBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

        self.platforms = {
            'facebook': 'https://facebook.com/',
            'twitter': 'https://twitter.com/',
            'instagram': 'https://instagram.com/',
            'linkedin': 'https://linkedin.com/in/',
            'github': 'https://github.com/',
            'youtube': 'https://youtube.com/@',
            'twitch': 'https://twitch.tv/',
        }

        self.search_count = 0
        self.start_time = datetime.now()

    async def setup_hook(self):
        await self.add_cog(SearchCog(self))
        await self.add_cog(StatsCog(self))

    async def on_ready(self):
        print(f'Bot is ready! Logged in as {self.user.name}')
        print('------')

class SearchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def check_username_availability(self, username: str) -> Dict[str, bool]:
        results = {}
        for platform, base_url in self.bot.platforms.items():
            try:
                url = f"{base_url}{username}"
                async with self.session.get(url) as response:
                    results[platform] = response.status == 404
            except Exception as e:
                print(f"Error checking {platform}: {str(e)}")
                results[platform] = None
        return results

    @commands.command(name='namesearch')
    async def name_search(self, ctx, *, name: str):
        self.bot.search_count += 1
        await ctx.send(f"🔎 Searching for '{name}' across social media...")

        embed = discord.Embed(
            title=f"Search Results for {name}",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Google",
            value=f"[Search on Google](https://www.google.com/search?q={name.replace(' ', '+')})",
            inline=False
        )

        for platform, base_url in self.bot.platforms.items():
            profile_url = f"{base_url}{name.replace(' ', '')}"
            embed.add_field(
                name=platform.capitalize(),
                value=f"[Check on {platform.capitalize()}]({profile_url})",
                inline=True
            )

        await ctx.send(embed=embed)

    @commands.command(name='username')
    async def username_search(self, ctx, username: str):
        self.bot.search_count += 1
        await ctx.send(f"🔍 Checking availability for username: {username}")

        if not re.match("^[A-Za-z0-9_-]+$", username):
            await ctx.send("❌ Invalid username format. Use only letters, numbers, underscores, and hyphens.")
            return

        embed = discord.Embed(
            title=f"Username Availability: {username}",
            color=discord.Color.green()
        )

        results = await self.check_username_availability(username)

        for platform, available in results.items():
            status = "✅ Available" if available else "❌ Taken"
            if available is None:
                status = "⚠️ Error checking"

            embed.add_field(
                name=platform.capitalize(),
                value=f"{status}\n[Check]({self.bot.platforms[platform]}{username})",
                inline=True
            )

        await ctx.send(embed=embed)

    def cog_unload(self):
        asyncio.create_task(self.session.close())

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='stats')
    async def show_stats(self, ctx):
        uptime = datetime.now() - self.bot.start_time
        embed = discord.Embed(
            title="Bot Statistics",
            color=discord.Color.blue()
        )
        embed.add_field(name="Total Searches", value=str(self.bot.search_count), inline=False)
        embed.add_field(name="Uptime", value=str(uptime).split('.')[0], inline=False)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=False)
        await ctx.send(embed=embed)

async def main():
    bot = SearchBot()
    token = os.getenv("DISCORD_BOT_TOKEN")  # Fetch token from environment variable
    if not token:
        print("Error: DISCORD_BOT_TOKEN is not set!")
        return
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())