import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Bonjour {user.mention_html()} ! 👋\n\n"
        "Je suis votre bot Telegram. Voici ce que je peux faire :\n\n"
        "/start - Afficher ce message de bienvenue\n"
        "/aide - Afficher l'aide\n"
        "/info - Afficher vos informations\n"
        "/echo [texte] - Répéter votre texte\n\n"
        "Ou envoyez-moi simplement un message et je vous répondrai ! 😊"
    )


async def aide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📚 Aide du bot\n\n"
        "Commandes disponibles :\n"
        "• /start - Démarrer le bot\n"
        "• /aide - Afficher cette aide\n"
        "• /info - Voir vos informations\n"
        "• /echo [texte] - Répéter un texte\n\n"
        "Vous pouvez aussi m'envoyer n'importe quel message et je vous répondrai."
    )


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"👤 Vos informations :\n\n"
        f"ID utilisateur : {user.id}\n"
        f"Prénom : {user.first_name}\n"
        f"Nom : {user.last_name or 'Non défini'}\n"
        f"Username : @{user.username or 'Non défini'}\n"
        f"ID du chat : {chat.id}\n"
        f"Type de chat : {chat.type}"
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        texte = " ".join(context.args)
        await update.message.reply_text(f"🔁 {texte}")
    else:
        await update.message.reply_text(
            "Usage : /echo [votre texte]\nExemple : /echo Bonjour le monde !"
        )


async def repondre_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texte = update.message.text
    await update.message.reply_text(
        f"Vous avez dit : « {texte} »\n\n"
        "Tapez /aide pour voir les commandes disponibles."
    )


async def erreur(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Une erreur s'est produite : %s", context.error)


def main() -> None:
    token = os.environ.get("8636518862:AAGZDQJMzlxQklGi4DfCXWN7N2WKr4IDMqU")
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN n'est pas défini. "
            "Ajoutez votre token dans les secrets ou dans le fichier .env"
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("aide", aide))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("echo", echo))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, repondre_message)
    )

    application.add_error_handler(erreur)

    logger.info("Bot démarré. Appuyez sur Ctrl+C pour arrêter.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
