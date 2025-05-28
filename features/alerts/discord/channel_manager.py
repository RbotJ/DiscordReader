    import logging
    from typing import Dict, Optional
    import discord
    from discord import app_commands
    from discord.ext import commands
    from sqlalchemy.orm import Session
    from common.db import get_db_session
    from common.models import DiscordChannel, AlertChannelMap

    logger = logging.getLogger(__name__)

    class ChannelManager:
        """
        Manages Discord channel discovery and alert routing using a database backend
        """

        def __init__(self, bot: commands.Bot):
            self.bot = bot

        async def discover_channels(self):
            """
            Discover all text channels and store them in the database if not already present
            """
            session: Session = get_db_session()
            discovered = 0

            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if not session.query(DiscordChannel).filter_by(channel_id=str(channel.id)).first():
                        new_channel = DiscordChannel(
                            guild_id=str(guild.id),
                            channel_id=str(channel.id),
                            name=channel.name,
                            channel_type='text'
                        )
                        session.add(new_channel)
                        discovered += 1

            session.commit()
            logger.info(f"✅ Discovered and stored {discovered} new text channels.")

        def set_alert_channel(self, alert_type: str, channel_id: int) -> bool:
            """
            Assign a channel to an alert type in the database
            """
            session: Session = get_db_session()
            existing = session.query(AlertChannelMap).filter_by(alert_type=alert_type).first()
            if existing:
                existing.channel_id = str(channel_id)
            else:
                session.add(AlertChannelMap(alert_type=alert_type, channel_id=str(channel_id)))

            session.commit()
            logger.info(f"✅ Alert type '{alert_type}' mapped to channel ID {channel_id}.")
            return True

        def get_alert_channel(self, alert_type: str) -> Optional[discord.TextChannel]:
            """
            Get the Discord channel object for a given alert type from the DB
            """
            session: Session = get_db_session()
            mapping = session.query(AlertChannelMap).filter_by(alert_type=alert_type).first()
            if not mapping:
                logger.warning(f"⚠️ No mapping found for alert type: {alert_type}")
                return None

            channel = self.bot.get_channel(int(mapping.channel_id))
            if not channel:
                logger.warning(f"⚠️ Channel with ID {mapping.channel_id} not found in Discord cache.")
            return channel

        def list_alert_mappings(self) -> Dict[str, str]:
            """
            Return a dictionary of alert type to channel name mappings
            """
            session: Session = get_db_session()
            results = {}
            for mapping in session.query(AlertChannelMap).all():
                channel = self.bot.get_channel(int(mapping.channel_id))
                results[mapping.alert_type] = channel.name if channel else f"Unknown (ID: {mapping.channel_id})"
            return results


    def setup(bot: commands.Bot):
        bot.channel_manager = ChannelManager(bot)

        @bot.event
        async def on_ready():
            logger.info(f"{bot.user.name} is ready. Discovering channels...")
            await bot.channel_manager.discover_channels()

        register_channel_commands(bot)


    def register_channel_commands(bot: commands.Bot):
        alert_group = app_commands.Group(name="alert", description="Commands for managing alerts")

        @alert_group.command(name="set_channel", description="Assign a Discord channel to an alert type")
        @app_commands.describe(alert_type="The type of alert", channel="The channel to use")
        async def set_alert_channel(interaction: discord.Interaction, alert_type: str, channel: discord.TextChannel):
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message("❌ Missing permissions.", ephemeral=True)
                return

            success = bot.channel_manager.set_alert_channel(alert_type, channel.id)
            if success:
                await interaction.response.send_message(f"✅ Alert '{alert_type}' mapped to #{channel.name}.", ephemeral=True)

        @alert_group.command(name="list_channels", description="List alert-channel mappings")
        async def list_alert_channels(interaction: discord.Interaction):
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message("❌ Missing permissions.", ephemeral=True)
                return

            mappings = bot.channel_manager.list_alert_mappings()
            if not mappings:
                await interaction.response.send_message("No alert channels configured.", ephemeral=True)
                return

            response = "📢 **Alert Channel Mappings**\n\n" + "\n".join(
                f"• **{atype}** → #{cname}" for atype, cname in mappings.items()
            )
            await interaction.response.send_message(response, ephemeral=True)

        bot.tree.add_command(alert_group)
