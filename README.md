# Vouch Bot

A Discord bot for vouches: users run `/vouch`, pick who they're vouching for,
how many videos, and the payment method used. The vouch goes to a mod
channel for Approve/Deny, and only posts publicly once approved.

## Commands

- `/vouch user videos payment` — submit a vouch (goes to mod channel first)
- `/vouches [user]` — check someone's approved vouch count (defaults to yourself)

## Setup

1. **Create the bot application**
   - Go to https://discord.com/developers/applications → New Application
   - Go to the "Bot" tab → Reset Token → copy it (this is your `DISCORD_TOKEN`)
   - Under "Privileged Gateway Intents", enable **Server Members Intent**

2. **Invite the bot to your server**
   - Go to the "OAuth2" → "URL Generator" tab
   - Scopes: check `bot` and `applications.commands`
   - Bot Permissions: check `Send Messages`, `Embed Links`, `Read Message History`, `View Channels`
   - Open the generated URL and add the bot to your server

3. **Get your IDs** (enable Developer Mode in Discord: User Settings → Advanced → Developer Mode)
   - Right-click your server icon → Copy Server ID → `GUILD_ID`
   - Right-click the mod-only approval channel → Copy Channel ID → `MOD_CHANNEL_ID`
   - Right-click the public vouch channel → Copy Channel ID → `VOUCH_CHANNEL_ID`
   - Right-click your mod role → Copy Role ID → `MOD_ROLE_ID` (optional — anyone with
     "Manage Server" permission can already approve/deny)

4. **Configure**
   ```bash
   cd vouch-bot
   cp .env.example .env
   # then fill in the values in .env
   ```

5. **Install and run**
   ```bash
   pip install -r requirements.txt
   python bot.py
   ```

   If it's working, you'll see `Synced N command(s).` and `Logged in as ...`
   in the console. The `/vouch` and `/vouches` commands should then appear
   in your server (may take a minute to show up the first time).

## Notes

- Vouch counts are stored in `vouch_data.json`, created automatically next to `bot.py`.
- Only users with the configured mod role or "Manage Server" permission can
  press Approve/Deny.
- Payment method is a fixed dropdown (PayPal, Cash App, Crypto, Bank Transfer,
  Other) — edit the `PAYMENT_CHOICES` list near the top of `bot.py` to change these.
- The bot needs to stay running to work. For 24/7 uptime you'll want to host
  it somewhere (a VPS, Railway, Replit, etc.) rather than running it on your
  own machine.
