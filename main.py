import os
import logging
import speech_recognition as sr
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import openai

openAiKey = ''
TOKEN = ''

openai.api_key = openAiKey

logging.basicConfig(level=logging.INFO)

def transcribe_audio(audio_file):
    recognizer = sr.Recognizer()
    try:
        logging.info(f"Проверка наличия файла: {audio_file}")
        if not os.path.exists(audio_file):
            logging.error(f"Файл не найден: {audio_file}")
            return "Аудиофайл не найден."

        with sr.AudioFile(audio_file) as source:
            logging.info("Чтение аудиофайла для транскрипции...")
            audio = recognizer.record(source)

        logging.info("Начало транскрипции...")
        text = recognizer.recognize_google(audio, language='ru-RU')
        logging.info(f"Транскрипция завершена: {text}")
        return text

    except sr.UnknownValueError:
        logging.error("Google Speech Recognition не смог распознать аудио")
        return "Не удалось распознать аудио."
    except sr.RequestError as e:
        logging.error(f"Ошибка сервиса Google Speech Recognition: {e}")
        return "Ошибка при запросе к Google Speech Recognition."
    except Exception as e:
        logging.error(f"Неизвестная ошибка при транскрипции: {e}")
        return f"Ошибка: {e}"

async def improve_conversation(text):
    logging.info("Отправка текста в GPT для улучшения...")
    try:
        response = openai.ChatCompletion.create( 
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Вы - полезный помощник."},
                {"role": "user", "content": f"Как можно улучшить этот текст:\n{text}"}
            ],
            max_tokens=1500,
            temperature=0.5,
            top_p=1
        )
        logging.info("Ответ от GPT получен.")
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"Ошибка при отправке запроса: {e}")
        return "Произошла ошибка при обработке запроса."

async def start(update: Update, context):
    await update.message.reply_text("Привет! Отправь мне аудиозапись, и я улучшу разговор.")

async def handle_audio(update: Update, context):
    file = await update.message.voice.get_file()
    file_path = f"{file.file_id}.ogg"

    logging.info(f"Загрузка файла {file_path}...")
    await file.download_to_drive(file_path)

    wav_file_path = file_path.replace('.ogg', '.wav')
    logging.info(f"Конвертация {file_path} в {wav_file_path}...")
    os.system(f"ffmpeg -i {file_path} {wav_file_path}")

    if not os.path.exists(wav_file_path):
        logging.error(f"Ошибка: wav-файл не создан")
        await update.message.reply_text("Ошибка: wav-файл не создан.")
        return

    try:
        logging.info("Чтение аудиофайла для транскрипции...")
        transcript = transcribe_audio(wav_file_path)
        await update.message.reply_text(f"Транскрипция: {transcript}")

        improved_text = await improve_conversation(transcript)
        await update.message.reply_text(f"Предложение по улучшению: {improved_text}")

    except Exception as e:
        logging.error(f"Ошибка при обработке аудио: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")

    finally:
        logging.info(f"Удаление файлов: {file_path}, {wav_file_path}")
        os.remove(file_path)
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))

    logging.info("Бот запущен!")
    app.run_polling()
