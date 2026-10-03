# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import asyncio 
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message 
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, STRING_SESSION, CHANNEL_ID, WAITING_TIME
from database.db import db
from TechVJ.strings import HELP_TXT
from bot import TechVJUser

class batch_temp(object):
    # One queue per user. A user's links are processed automatically in order.
    QUEUES = {}
    WORKERS = {}
    CANCEL_EVENTS = {}

async def downstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break

        await asyncio.sleep(3)
      
    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Downloaded:** **{txt}**")
            await asyncio.sleep(10)
        except:
            await asyncio.sleep(5)


# upload status
async def upstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break

        await asyncio.sleep(3)      
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Uploaded:** **{txt}**")
            await asyncio.sleep(10)
        except:
            await asyncio.sleep(5)


# progress writer
def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")


# start command
@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
    buttons = [[
        InlineKeyboardButton("❣️ Developer", url = "https://t.me/kingvj01")
    ],[
        InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/vj_bot_disscussion'),
        InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/vj_bots')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await client.send_message(
        chat_id=message.chat.id, 
        text=f"<b>👋 Hi {message.from_user.mention}, I am Save Restricted Content Bot, I can send you restricted content by its post link.\n\nFor downloading restricted content /login first.\n\nKnow how to use bot by - /help</b>", 
        reply_markup=reply_markup, 
        reply_to_message_id=message.id
    )
    return


# help command
@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    await client.send_message(
        chat_id=message.chat.id, 
        text=f"{HELP_TXT}"
    )

# cancel command
@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client, message: Message):
    user_id = message.from_user.id
    cancel_event = batch_temp.CANCEL_EVENTS.get(user_id)

    if cancel_event:
        cancel_event.set()

    queue = batch_temp.QUEUES.get(user_id)
    cleared = 0
    if queue:
        while not queue.empty():
            try:
                queue.get_nowait()
                queue.task_done()
                cleared += 1
            except asyncio.QueueEmpty:
                break

    if cancel_event or cleared:
        await client.send_message(
            message.chat.id,
            f"**Current task will be cancelled and {cleared} queued link(s) removed.**"
        )
    else:
        await client.send_message(
            message.chat.id,
            "**No active or queued task found.**"
        )


async def process_link(client: Client, message: Message, cancel_event: asyncio.Event):
    datas = message.text.split("/")
    temp = datas[-1].replace("?single", "").split("-")

    try:
        fromID = int(temp[0].strip())
        try:
            toID = int(temp[1].strip())
        except:
            toID = fromID
    except (ValueError, IndexError):
        await message.reply_text("**Invalid Telegram link.**")
        return

    if LOGIN_SYSTEM == True:
        user_data = await db.get_session(message.from_user.id)
        if user_data is None:
            await message.reply(
                "**For Downloading Restricted Content You Have To /login First.**"
            )
            return

        api_id = int(await db.get_api_id(message.from_user.id))
        api_hash = await db.get_api_hash(message.from_user.id)

        try:
            acc = Client(
                "saverestricted",
                session_string=user_data,
                api_hash=api_hash,
                api_id=api_id
            )
            await acc.connect()
        except:
            await message.reply(
                "**Your Login Session Expired. So /logout First Then Login Again By - /login**"
            )
            return
    else:
        if TechVJUser is None:
            await client.send_message(
                message.chat.id,
                "**String Session is not Set**",
                reply_to_message_id=message.id
            )
            return
        acc = TechVJUser

    try:
        for msgid in range(fromID, toID + 1):
            if cancel_event.is_set():
                break

            # private
            if "https://t.me/c/" in message.text:
                chatid = int("-100" + datas[4])
                try:
                    await handle_private(client, acc, message, chatid, msgid, cancel_event)
                except Exception as e:
                    if ERROR_MESSAGE == True:
                        await client.send_message(
                            message.chat.id,
                            f"Error: {e}",
                            reply_to_message_id=message.id
                        )

            # bot
            elif "https://t.me/b/" in message.text:
                username = datas[4]
                try:
                    await handle_private(client, acc, message, username, msgid, cancel_event)
                except Exception as e:
                    if ERROR_MESSAGE == True:
                        await client.send_message(
                            message.chat.id,
                            f"Error: {e}",
                            reply_to_message_id=message.id
                        )

            # public
            else:
                username = datas[3]

                try:
                    msg = await client.get_messages(username, msgid)
                except UsernameNotOccupied:
                    await client.send_message(
                        message.chat.id,
                        "The username is not occupied by anyone",
                        reply_to_message_id=message.id
                    )
                    return

                try:
                    await client.copy_message(
                        message.chat.id,
                        msg.chat.id,
                        msg.id,
                        reply_to_message_id=message.id
                    )
                except:
                    try:
                        await handle_private(
                            client, acc, message, username, msgid, cancel_event
                        )
                    except Exception as e:
                        if ERROR_MESSAGE == True:
                            await client.send_message(
                                message.chat.id,
                                f"Error: {e}",
                                reply_to_message_id=message.id
                            )

            if cancel_event.is_set():
                break

            # Keep the existing flood-wait protection between messages.
            await asyncio.sleep(WAITING_TIME)

    finally:
        if LOGIN_SYSTEM == True:
            try:
                await acc.disconnect()
            except:
                pass


async def queue_worker(user_id):
    queue = batch_temp.QUEUES[user_id]
    cancel_event = batch_temp.CANCEL_EVENTS[user_id]

    try:
        while not queue.empty():
            try:
                client, message = await queue.get()
            except asyncio.CancelledError:
                break

            try:
                cancel_event.clear()
                position_text = "Processing your queued link..."
                await message.reply_text(position_text)
                await process_link(client, message, cancel_event)
            except Exception as e:
                if ERROR_MESSAGE == True:
                    try:
                        await message.reply_text(f"Error: {e}")
                    except:
                        pass
            finally:
                queue.task_done()

                # Cancellation applies to the current batch and clears waiting items.
                if cancel_event.is_set():
                    while not queue.empty():
                        try:
                            queue.get_nowait()
                            queue.task_done()
                        except asyncio.QueueEmpty:
                            break
                    break
    finally:
        batch_temp.WORKERS.pop(user_id, None)
        batch_temp.CANCEL_EVENTS.pop(user_id, None)
        if queue.empty():
            batch_temp.QUEUES.pop(user_id, None)


@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    # Joining chat
    if ("https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text) and LOGIN_SYSTEM == False:
        if TechVJUser is None:
            await client.send_message(
                message.chat.id,
                "String Session is not Set",
                reply_to_message_id=message.id
            )
            return

        try:
            try:
                await TechVJUser.join_chat(message.text)
            except Exception as e:
                await client.send_message(
                    message.chat.id,
                    f"Error : {e}",
                    reply_to_message_id=message.id
                )
                return
            await client.send_message(
                message.chat.id,
                "Chat Joined",
                reply_to_message_id=message.id
            )
        except UserAlreadyParticipant:
            await client.send_message(
                message.chat.id,
                "Chat already Joined",
                reply_to_message_id=message.id
            )
        except InviteHashExpired:
            await client.send_message(
                message.chat.id,
                "Invalid Link",
                reply_to_message_id=message.id
            )
        return

    if "https://t.me/" not in message.text:
        return

    user_id = message.from_user.id

    # Queue every new link instead of rejecting it while another task is running.
    queue = batch_temp.QUEUES.setdefault(user_id, asyncio.Queue())
    cancel_event = batch_temp.CANCEL_EVENTS.setdefault(user_id, asyncio.Event())

    await queue.put((client, message))
    position = queue.qsize()

    if position == 1 and user_id not in batch_temp.WORKERS:
        await message.reply_text("**Link added. Processing now...**")
    else:
        await message.reply_text(
            f"**Link added to queue. Position: {position}**\n"
            "It will start automatically after the previous task finishes."
        )

    if user_id not in batch_temp.WORKERS:
        worker = asyncio.create_task(queue_worker(user_id))
        batch_temp.WORKERS[user_id] = worker


async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int, cancel_event=None):
    msg: Message = await acc.get_messages(chatid, msgid)
    if msg.empty: return 
    msg_type = get_message_type(msg)
    if not msg_type: return 
    if CHANNEL_ID:
        try:
            chat = int(CHANNEL_ID)
        except:
            chat = message.chat.id
    else:
        chat = message.chat.id
    if cancel_event and cancel_event.is_set(): return 
    if "Text" == msg_type:
        try:
            await client.send_message(chat, msg.text, entities=msg.entities, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            return 
        except Exception as e:
            if ERROR_MESSAGE == True:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            return 

    smsg = await client.send_message(message.chat.id, '**Downloading**', reply_to_message_id=message.id)
    asyncio.create_task(downstatus(client, f'{message.id}downstatus.txt', smsg, chat))
    try:
        file = await acc.download_media(msg, progress=progress, progress_args=[message,"down"])
        os.remove(f'{message.id}downstatus.txt')
    except Exception as e:
        if ERROR_MESSAGE == True:
            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML) 
        return await smsg.delete()
    if batch_temp.IS_BATCH.get(message.from_user.id): return 
    asyncio.create_task(upstatus(client, f'{message.id}upstatus.txt', smsg, chat))

    if msg.caption:
        caption = msg.caption
    else:
        caption = None
    if batch_temp.IS_BATCH.get(message.from_user.id): return 
            
    if "Document" == msg_type:
        try:
            ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
        except:
            ph_path = None
        
        try:
            await client.send_document(chat, file, thumb=ph_path, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML, progress=progress, progress_args=[message,"up"])
        except Exception as e:
            if ERROR_MESSAGE == True:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        if ph_path != None: os.remove(ph_path)
        

    elif "Video" == msg_type:
        try:
            ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
        except:
            ph_path = None
        
        try:
            await client.send_video(chat, file, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, thumb=ph_path, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML, progress=progress, progress_args=[message,"up"])
        except Exception as e:
            if ERROR_MESSAGE == True:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        if ph_path != None: os.remove(ph_path)

    elif "Animation" == msg_type:
        try:
            await client.send_animation(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            if ERROR_MESSAGE == True:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        
    elif "Sticker" == msg_type:
        try:
            await client.send_sticker(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            if ERROR_MESSAGE == True:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)     

    elif "Voice" == msg_type:
        try:
            await client.send_voice(chat, file, caption=caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML, progress=progress, progress_args=[message,"up"])
        except Exception as e:
            if ERROR_MESSAGE == True:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    elif "Audio" == msg_type:
        try:
            ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
        except:
            ph_path = None

        try:
            await client.send_audio(chat, file, thumb=ph_path, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML, progress=progress, progress_args=[message,"up"])   
        except Exception as e:
            if ERROR_MESSAGE == True:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        
        if ph_path != None: os.remove(ph_path)

    elif "Photo" == msg_type:
        try:
            await client.send_photo(chat, file, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        except:
            if ERROR_MESSAGE == True:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
    
    if os.path.exists(f'{message.id}upstatus.txt'): 
        os.remove(f'{message.id}upstatus.txt')
        os.remove(file)
    await client.delete_messages(message.chat.id,[smsg.id])


# get the type of message
def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    try:
        msg.document.file_id
        return "Document"
    except:
        pass

    try:
        msg.video.file_id
        return "Video"
    except:
        pass

    try:
        msg.animation.file_id
        return "Animation"
    except:
        pass

    try:
        msg.sticker.file_id
        return "Sticker"
    except:
        pass

    try:
        msg.voice.file_id
        return "Voice"
    except:
        pass

    try:
        msg.audio.file_id
        return "Audio"
    except:
        pass

    try:
        msg.photo.file_id
        return "Photo"
    except:
        pass

    try:
        msg.text
        return "Text"
    except:
        pass
        

# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01
