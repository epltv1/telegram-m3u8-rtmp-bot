import subprocess
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dictionary to keep track of running FFmpeg processes
processes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        'Hi! I am a streaming bot. Use /stream <m3u8_url> <rtmp_url> <stream_key> to start streaming.\n'
        'Example: /stream http://example.com/playlist.m3u8 rtmp://your-rtmp-server/live your_stream_key\n'
        'Use /stop to stop the current stream.'
    )

async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /stream command to start streaming M3U8 to RTMP."""
    user_id = update.effective_user.id
    args = context.args

    # Check if the correct number of arguments is provided
    if len(args) != 3:
        await update.message.reply_text(
            'Usage: /stream <m3u8_url> <rtmp_url> <stream_key>\n'
            'Example: /stream http://example.com/playlist.m3u8 rtmp://your-rtmp-server/live your_stream_key'
        )
        return

    m3u8_url, rtmp_url, stream_key = args
    full_rtmp_url = f"{rtmp_url}/{stream_key}"

    # Check if a stream is already running for this user
    if user_id in processes:
        await update.message.reply_text('A stream is already running. Use /stop to stop it first.')
        return

    try:
        # FFmpeg command to stream M3U8 to RTMP
        ffmpeg_cmd = [
            'ffmpeg',
            '-re',  # Read input at native frame rate
            '-i', m3u8_url,  # Input M3U8 URL
            '-c:v', 'libx264',  # Video codec
            '-preset', 'veryfast',  # Encoding speed
            '-b:v', '3500k',  # Video bitrate
            '-maxrate', '3500k',  # Max bitrate
            '-bufsize', '7000k',  # Buffer size
            '-pix_fmt', 'yuv420p',  # Pixel format
            '-g', '50',  # GOP size
            '-c:a', 'aac',  # Audio codec
            '-b:a', '160k',  # Audio bitrate
            '-ac', '2',  # Audio channels
            '-ar', '44100',  # Audio sample rate
            '-f', 'flv',  # Output format
            full_rtmp_url  # RTMP destination
        ]

        # Start FFmpeg process
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes[user_id] = process
        await update.message.reply_text(f'Started streaming from {m3u8_url} to {full_rtmp_url}.')

    except Exception as e:
        await update.message.reply_text(f'Error starting stream: {str(e)}')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /stop command to stop the current stream."""
    user_id = update.effective_user.id

    if user_id not in processes:
        await update.message.reply_text('No stream is currently running.')
        return

    # Terminate the FFmpeg process
    process = processes[user_id]
    process.terminate()
    try:
        process.wait(timeout=5)  # Wait for the process to terminate
    except subprocess.TimeoutExpired:
        process.kill()  # Force kill if it doesn't terminate
    del processes[user_id]
    await update.message.reply_text('Stream stopped.')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f'Update {update} caused error {context.error}')
    if update and update.message:
        await update.message.reply_text('An error occurred. Please try again.')

def main():
    """Start the bot."""
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    bot_token = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')
    
    # Create the Application
    application = Application.builder().token(bot_token).build()

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stream', stream))
    application.add_handler(CommandHandler('stop', stop))
    application.add_error_handler(error_handler)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
