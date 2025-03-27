import discord
from discord import app_commands
from discord.ext import tasks
from pathlib import Path
import os
import json
import asyncio
import datetime
import threading
from connection_manager import ConnectionManager
import time

# Discord bot configuration
DISCORD_TOKEN = "MTM0MjU4MTMyNTAxNzY0OTE3Mg.GFaUKh.6h2Ljs3boRwEc7evYcZ8kNtXyyd72RCEjxJnik"

class ConnectionBot(discord.Client):
    _instance = None
    _lock = threading.Lock()
    _bot_thread = None
    
    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance of ConnectionBot"""
        with cls._lock:
            if cls._instance is None:
                print("Initializing Discord bot...")
                cls._instance = cls()
                # Start the bot in a separate thread if not already running
                if cls._bot_thread is None or not cls._bot_thread.is_alive():
                    cls._bot_thread = threading.Thread(target=cls._instance._run_bot, daemon=True)
                    cls._bot_thread.start()
            return cls._instance
    
    def __init__(self):
        if self.__class__._instance is not None:
            raise RuntimeError("This class is a singleton! Use get_instance() instead.")
            
        # Enable all intents
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        
        self.status_file = Path(__file__).parent / "connection_status.txt"
        self.config_file = Path(__file__).parent / "discord_config.json"
        self.notification_channel_id = self.load_config().get('channel_id')
        self.tree = app_commands.CommandTree(self)
        
        # Initialize ConnectionManager
        self.connection_manager = None
        self.is_ready = threading.Event()
        
    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {}
        
    def save_config(self, channel_id):
        with open(self.config_file, 'w') as f:
            json.dump({'channel_id': channel_id}, f)
    
    def get_device_status(self):
        """Get the current status of all devices with timestamp"""
        # Format time as HH:MMam/pm
        current_time = datetime.datetime.now()
        hour = current_time.hour
        am_pm = "am" if hour < 12 else "pm"
        if hour > 12:
            hour -= 12
        if hour == 0:
            hour = 12
        formatted_time = f"{hour}:{current_time.minute:02d}{am_pm}"
        
        status_lines = [f"Current Device Status TIME ({formatted_time}):"]
        
        if self.connection_manager:
            current_devices = self.connection_manager.get_available_devices()
            
            # Show connected devices
            for name, info in current_devices.items():
                status_lines.append(f"+ {name} ({info['connection_type']} - {info['device_id']})")
                
            # Show disconnected devices
            for device_id, info in self.connection_manager.device_config["devices"].items():
                friendly_name = info["friendly_name"]
                if friendly_name not in current_devices:
                    status_lines.append(f"X {friendly_name}: disconnected")
        else:
            status_lines.append("ConnectionManager not initialized")
            
        return status_lines
    
    def send_notification(self, message):
        """Send a notification to the configured Discord channel
        
        This method can be called directly from other modules
        without needing to write to a file
        """
        if not self.is_ready.is_set():
            # If bot is not ready, write to file as fallback
            with open(self.status_file, "a") as f:
                f.write(f"{message}\n")
            return
            
        if not self.notification_channel_id:
            print("No notification channel configured")
            return
            
        asyncio.run_coroutine_threadsafe(
            self._send_notification_async(message),
            self.loop
        )
        
    async def _send_notification_async(self, message):
        """Internal async method to send notification"""
        try:
            channel = self.get_channel(self.notification_channel_id)
            if channel:
                # Format the message
                if ":" in message:
                    device, status = message.split(":", 1)
                    embed = discord.Embed(
                        title="Device Connection Changes",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name=device.strip(),
                        value=status.strip(),
                        inline=False
                    )
                    await channel.send(embed=embed)
                else:
                    await channel.send(message)
        except Exception as e:
            print(f"Error sending notification: {e}")
        
    async def setup_hook(self):
        # Register the slash command
        self.tree.add_command(app_commands.Command(
            name="status",
            description="Get the current status of all connected devices",
            callback=self.status_command
        ))
        await self.tree.sync()
        
        # Start the status check loop
        self.check_status.start()
        
    async def status_command(self, interaction):
        """Callback for the /status command"""
        await interaction.response.defer()
        
        # Initialize ConnectionManager if not already done
        if not self.connection_manager:
            self.connection_manager = ConnectionManager.get_instance()
            # Wait for ConnectionManager to initialize
            await asyncio.sleep(3)
            
        status_lines = self.get_device_status()
        
        # Create an embed for the response
        embed = discord.Embed(
            title="Device Status",
            description=status_lines[0],
            color=discord.Color.blue()
        )
        
        # Add connected and disconnected devices to the embed
        connected_devices = []
        disconnected_devices = []
        
        for line in status_lines[1:]:
            if line.startswith("+"):
                connected_devices.append(line[2:])  # Remove the "+ " prefix
            elif line.startswith("X"):
                disconnected_devices.append(line[2:])  # Remove the "X " prefix
                
        if connected_devices:
            embed.add_field(
                name="Connected Devices",
                value="\n".join(connected_devices),
                inline=False
            )
            
        if disconnected_devices:
            embed.add_field(
                name="Disconnected Devices",
                value="\n".join(disconnected_devices),
                inline=False
            )
            
        await interaction.followup.send(embed=embed)
        
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print(f'Bot ID: {self.user.id}')
        print('Permissions:')
        print('- Send Messages')
        print('- Embed Links')
        print('- Read Messages')
        print('\nUse !setchannel in your desired Discord channel to receive notifications')
        print('Use /status to get the current device status')
        
        # Initialize ConnectionManager
        self.connection_manager = ConnectionManager.get_instance()
        # Wait for ConnectionManager to initialize
        await asyncio.sleep(3)
        
        # Signal that the bot is ready
        self.is_ready.set()
        
    async def on_message(self, message):
        print(f"\nReceived message from {message.author} in {message.channel}:")
        print(f"Content: {message.content}")
        print(f"Channel ID: {message.channel.id}")
        
        if message.author == self.user:
            print("Message was from self, ignoring")
            return
            
        if message.content.startswith('!setchannel'):
            print(f"Setting channel to: {message.channel.id}")
            self.notification_channel_id = message.channel.id
            self.save_config(message.channel.id)
            try:
                await message.channel.send('I will send connection notifications to this channel')
                print("Successfully sent confirmation message")
            except Exception as e:
                print(f"Error sending confirmation: {e}")
                
    @tasks.loop(seconds=1.0)
    async def check_status(self):
        try:
            if self.status_file.exists():
                content = self.status_file.read_text()
                if content and self.notification_channel_id:
                    channel = self.get_channel(self.notification_channel_id)
                    if channel:
                        # Format the message
                        lines = content.strip().split("\n")
                        embed = discord.Embed(
                            title="Device Connection Changes",
                            color=discord.Color.blue()
                        )
                        
                        for line in lines:
                            if line:
                                device, status = line.split(":", 1)
                                embed.add_field(
                                    name=device.strip(),
                                    value=status.strip(),
                                    inline=False
                                )
                                
                        await channel.send(embed=embed)
                        
                    # Clear the file after processing
                    self.status_file.write_text("")
                    
        except Exception as e:
            print(f"Error checking status: {e}")
            
    @check_status.before_loop
    async def before_check_status(self):
        await self.wait_until_ready()
        
    def _run_bot(self):
        """Run the bot in a separate thread"""
        try:
            self.run(DISCORD_TOKEN)
        except Exception as e:
            print(f"Error running Discord bot: {e}")

def main():
    # Get singleton instance and wait for it to be ready
    bot = ConnectionBot.get_instance()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Bot shutdown requested")

if __name__ == "__main__":
    main()
