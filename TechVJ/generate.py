# Don't Remove Credit Tg - @VJ_Bots
import asyncio
import base64
import time
from io import BytesIO

import qrcode
from pyrogram import Client, filters, raw
from pyrogram.errors import RPCError
from pyrogram.types import Message

from config import API_ID, API_HASH
from database.db import db

QR_TIMEOUT = 300


def make_qr(token: bytes) -> BytesIO:
    encoded = base64.urlsafe_b64encode(token).decode("ascii").rstrip("=")
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(f"tg://login?token={encoded}")
    qr.make(fit=True)

    image = BytesIO()
    image.name = "telegram_login_qr.png"
    qr.make_image().save(image, format="PNG")
    image.seek(0)
    return image


async def send_qr(message: Message, token: bytes, caption: str):
    await message.reply_photo(photo=make_qr(token), caption=caption)


async def qr_login(client: Client, message: Message, api_id: int, api_hash: str):
    result = await client.invoke(
        raw.functions.auth.ExportLoginToken(
            api_id=api_id,
            api_hash=api_hash,
            except_ids=[]
        )
    )

    if isinstance(result, raw.types.auth.LoginTokenSuccess):
        return True

    if isinstance(result, raw.types.auth.LoginTokenMigrateTo):
        await message.reply("**Telegram requested another DC for this login.**\nPlease run /login again.")
        return False

    if not isinstance(result, raw.types.auth.LoginToken):
        raise RuntimeError(f"Unexpected Telegram QR response: {type(result).__name__}")

    await send_qr(
        message,
        result.token,
        "**Scan this QR with Telegram.**\n\n"
        "Telegram → Settings → Devices → Link Desktop Device\n"
        "Then scan the QR code above.\n\n"
        "No OTP is required."
    )

    deadline = time.monotonic() + QR_TIMEOUT

    while time.monotonic() < deadline:
        await asyncio.sleep(2)

        result = await client.invoke(
            raw.functions.auth.ExportLoginToken(
                api_id=api_id,
                api_hash=api_hash,
                except_ids=[]
            )
        )

        if isinstance(result, raw.types.auth.LoginTokenSuccess):
            return True

        if isinstance(result, raw.types.auth.LoginTokenMigrateTo):
            await message.reply("**Telegram requested another DC for this login.**\nPlease run /login again.")
            return False

        if isinstance(result, raw.types.auth.LoginToken):
            await send_qr(message, result.token, "**QR refreshed. Please scan this new QR.**")

    await message.reply("**QR login timed out. Run /login again.**")
    return False


@Client.on_message(filters.private & ~filters.forwarded & filters.command(["logout"]))
async def logout(client, message):
    if await db.get_session(message.from_user.id) is None:
        return
    await db.set_session(message.from_user.id, session=None)
    await message.reply("**Logout Successfully** ♦")


@Client.on_message(filters.private & ~filters.forwarded & filters.command(["login"]))
async def main(bot: Client, message: Message):
    user_id = int(message.from_user.id)

    if await db.get_session(user_id) is not None:
        await message.reply("**You Are Already Logged In. First /logout Your Old Session. Then Do Login.**")
        return

    await message.reply(
        "**Telegram QR Login**\n\n"
        "You will not need to send your phone number or OTP to this bot."
    )

    api_id_msg = await bot.ask(
        user_id,
        "<b>Send your Telegram API ID.\n\nUse /skip to use the bot's configured API credentials.</b>",
        filters=filters.text,
        timeout=300
    )

    if api_id_msg.text.strip() == "/skip":
        api_id = API_ID
        api_hash = API_HASH
    else:
        try:
            api_id = int(api_id_msg.text.strip())
        except ValueError:
            await api_id_msg.reply("**API ID must be an integer. Start again with /login.**")
            return

        api_hash_msg = await bot.ask(
            user_id,
            "**Now send your Telegram API Hash.**",
            filters=filters.text,
            timeout=300
        )

        if api_hash_msg.text.strip() == "/cancel":
            await api_hash_msg.reply("**Login cancelled.**")
            return

        api_hash = api_hash_msg.text.strip()

    client = Client(":memory:", api_id=api_id, api_hash=api_hash)

    try:
        await client.connect()

        success = await qr_login(client, message, api_id, api_hash)
        if not success:
            await client.disconnect()
            return

        session_string = await client.export_session_string()
        if not session_string:
            raise RuntimeError("Telegram returned an empty session string.")

        verify_client = Client(
            ":memory:",
            session_string=session_string,
            api_id=api_id,
            api_hash=api_hash
        )

        await verify_client.start()
        me = await verify_client.get_me()

        if not me:
            await verify_client.stop()
            raise RuntimeError("Telegram session verification failed.")

        await db.set_session(user_id, session=session_string)
        await db.set_api_id(user_id, api_id=api_id)
        await db.set_api_hash(user_id, api_hash=api_hash)

        await verify_client.stop()
        await client.disconnect()

        await bot.send_message(
            user_id,
            "**Account Login Successfully.**\n\nYour Telegram session has been saved."
        )

    except RPCError as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        await message.reply_text(f"**Telegram login failed:**\n\n{e}")

    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        await message.reply_text(f"**ERROR IN LOGIN:**\n\n{e}")
