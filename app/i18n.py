"""Bilingual interface strings. t(lang, key) returns Spanish, English, or both.

KB content stays in Spanish and is translated on the fly; these are the bot's
own interface strings, hand-written in both languages for accuracy.
"""

LANG_CHOICES = {"1": "es", "2": "en", "3": "both"}

STR = {
    "choose_lang": {
        "es": "🤝 Bienvenido/a a *Ayuda Venezuela*.\nElige idioma / Choose language:\n1) Español\n2) English\n3) Ambos / Both",
        "en": "🤝 Welcome to *Ayuda Venezuela*.\nElige idioma / Choose language:\n1) Español\n2) English\n3) Ambos / Both",
    },
    "menu": {
        "es": ("🇻🇪 *Ayuda Venezuela* — escribe el número o lo que necesitas:\n\n"
               "1 Buscar a una persona\n2 Avisar que alguien está bien\n"
               "3 Dónde quedarse (refugio)\n4 Comida y agua\n"
               "5 Atención médica / insumos\n6 Apoyo emocional\n"
               "7 Eventos de ayuda cerca\n"
               "8 *Red de héroes*: necesito ayuda o quiero ayudar\n"
               "9 Ver solicitudes de la red\n10 Cómo ayudar / donar seguro\n"
               "11 Verificar si algo es estafa\n\n"
               "Escribe IDIOMA para cambiar. BORRAR elimina tus datos."),
        "en": ("🇻🇪 *Ayuda Venezuela* — reply with a number or tell me what you need:\n\n"
               "1 Search for a person\n2 Mark someone safe\n"
               "3 Where to stay (shelter)\n4 Food & water\n"
               "5 Medical care / supplies\n6 Emotional support\n"
               "7 Local help events\n"
               "8 *Hero network*: I need help or I want to help\n"
               "9 See network requests\n10 How to help / donate safely\n"
               "11 Check if something is a scam\n\n"
               "Type LANGUAGE to change. DELETE removes your data."),
    },
    "error_generic": {
        "es": "Ups, algo salió mal de nuestro lado. Escribe MENU para empezar de nuevo.",
        "en": "Oops, something went wrong on our side. Type MENU to start again.",
    },
    "resolved_done": {
        "es": "✅ Marcamos tus solicitudes como resueltas. ¡Nos alegra que se haya resuelto! Escribe MENU para más.",
        "en": "✅ We marked your requests as resolved. So glad it worked out! Type MENU for more.",
    },
    "resolve_hint": {
        "es": "Cuando se resuelva, escribe RESUELTO para cerrarla.",
        "en": "When it's resolved, type RESOLVED to close it.",
    },
    "alerts_on": {
        "es": "🔔 Activadas las alertas de réplicas. Te avisaremos si hay un sismo fuerte cerca. Escribe ALERTAS para desactivar.",
        "en": "🔔 Aftershock alerts are ON. We'll warn you of a strong nearby quake. Type ALERTS to turn off.",
    },
    "alerts_off": {
        "es": "🔕 Alertas de réplicas desactivadas. Escribe ALERTAS para volver a activarlas.",
        "en": "🔕 Aftershock alerts are OFF. Type ALERTS to turn them back on.",
    },
    "notify_match": {
        "es": "🔔 ¡Nueva coincidencia para tu solicitud de {cat}! {desc} — {contact}\n⚠️ Nunca envíes dinero por adelantado. Escribe RESUELTO si ya no necesitas ayuda.",
        "en": "🔔 New match for your {cat} request! {desc} — {contact}\n⚠️ Never send money up front. Type RESOLVED if you no longer need help.",
    },
    "report_ask": {
        "es": "🛡️ Describe lo que pasó. Si tienes el contacto de la persona, inclúyelo. Nuestro equipo lo revisará.",
        "en": "🛡️ Describe what happened. If you have the person's contact, include it. Our team will review it.",
    },
    "report_done": {
        "es": "Gracias por avisar. Recibimos tu reporte y lo revisaremos. Si incluiste un contacto, pausamos sus publicaciones por precaución.",
        "en": "Thank you for flagging this. We received your report and will review it. If you included a contact, we paused their posts as a precaution.",
    },
    "block_ask": {
        "es": "¿Qué contacto quieres bloquear? Escribe su número o WhatsApp.",
        "en": "Which contact do you want to block? Send their number or WhatsApp.",
    },
    "block_done": {
        "es": "Listo. No volveremos a mostrarte a ese contacto.",
        "en": "Done. We won't show you that contact again.",
    },
    "banned": {
        "es": "Tu acceso fue suspendido por incumplir las normas de seguridad de la plataforma.",
        "en": "Your access has been suspended for violating the platform's safety rules.",
    },
    "minor_redirect": {
        "es": "Cuando hay un menor de edad, por seguridad *no* conectamos con desconocidos. Aquí tienes organizaciones de protección infantil:",
        "en": "When a minor is involved we *never* connect you with strangers, for safety. Here are child-protection organizations:",
    },
    "child_orgs": {
        "es": "• UNICEF Venezuela\n• Save the Children\n• Cruz Roja — Restablecimiento de Contacto: https://familylinks.icrc.org",
        "en": "• UNICEF Venezuela\n• Save the Children\n• Red Cross — Restoring Family Links: https://familylinks.icrc.org",
    },
    "safety_blocked": {
        "es": "⚠️ No pude publicar eso. Por seguridad bloqueamos mensajes que piden dinero por adelantado, contenido sexual, o que llevan fuera de la plataforma. Si fue un malentendido, reformúlalo sin esos elementos.",
        "en": "⚠️ I couldn't post that. For safety we block messages that ask for money up front, contain sexual content, or push people off-platform. If this was a mistake, rephrase it without those elements.",
    },
    "rate_limited": {
        "es": "Alcanzaste el límite de publicaciones por hoy. Inténtalo de nuevo mañana. Escribe MENU para otras opciones.",
        "en": "You've reached today's posting limit. Try again tomorrow. Type MENU for other options.",
    },
    "safety_card": {
        "es": "🛡️ Seguridad: reúnete en un lugar público y de día, avisa a alguien de confianza, *nunca* envíes dinero ni compartas códigos o contraseñas. Escribe REPORTAR si algo se siente raro.",
        "en": "🛡️ Safety: meet in a public place in daytime, tell someone you trust, *never* send money or share codes or passwords. Type REPORT if anything feels off.",
    },
    "verified_badge": {
        "es": "✓ verificado",
        "en": "✓ verified",
    },
    "share": {
        "es": ("📲 Comparte *Ayuda Venezuela* con quien lo necesite o quiera ayudar.\n"
               "Reenvía este enlace a tus grupos de WhatsApp:\n{link}\n\n"
               "Un mensaje puede ayudar a una familia a encontrarse. 🇻🇪"),
        "en": ("📲 Share *Ayuda Venezuela* with anyone who needs help or wants to help.\n"
               "Forward this link to your WhatsApp groups:\n{link}\n\n"
               "One message can help a family reunite. 🇻🇪"),
    },
    "cross_border_nudge": {
        "es": "🌎 ¿Necesitas ayuda de alguien en EE.UU., o quieres ayudar a Venezuela desde afuera? Puedo conectarte y traducir entre ustedes.",
        "en": "🌎 Need help from someone in the US, or want to help Venezuela from abroad? I can connect you and translate between you.",
    },
    "cross_border_tag": {
        "es": "🌎 a través de la frontera — traducido para ti",
        "en": "🌎 across the border — translated for you",
    },
    "ask_search_name": {
        "es": ("Escribe el *nombre completo* de la persona que buscas. "
               "Si puedes, agrega edad y ciudad separadas por comas.\n"
               "Ej: María Pérez, 34, La Guaira\n\n"
               "Consultaré los registros públicos en vivo. Escribe MENU para volver."),
        "en": ("Type the *full name* of the person you're looking for. "
               "If you can, add age and city separated by commas.\n"
               "E.g.: María Pérez, 34, La Guaira\n\n"
               "I'll query the public registries live. Type MENU to go back."),
    },
    "ask_role": {
        "es": "¿*Necesitas* ayuda o *quieres ayudar* (ser héroe/voluntario)?\nResponde: necesito / ayudar",
        "en": "Do you *need* help or *want to help* (be a hero/volunteer)?\nReply: need / help",
    },
    "ask_category": {
        "es": ("¿Qué tipo de ayuda? Responde con una palabra:\n"
               "• transporte • insumos • traduccion • informacion • busqueda\n"
               "• alojamiento • dinero • menores"),
        "en": ("What kind of help? Reply with one word:\n"
               "• transport • supplies • translation • information • search\n"
               "• housing • money • minors"),
    },
    "ask_mode": {
        "es": "¿Es ayuda *remota* (a distancia) o *presencial* (en persona)?\nResponde: remota / presencial",
        "en": "Is it *remote* help or *in person*?\nReply: remote / inperson",
    },
    "ask_region": {
        "es": "¿Dónde estás? Responde: EEUU / Venezuela / otro",
        "en": "Where are you? Reply: USA / Venezuela / other",
    },
    "ask_location": {
        "es": "¿Ciudad o zona? (ej. Caracas, La Guaira, Atlanta)",
        "en": "City or area? (e.g. Caracas, La Guaira, Atlanta)",
    },
    "ask_desc": {
        "es": "Describe en una frase lo que ofreces o necesitas.",
        "en": "Describe in one sentence what you offer or need.",
    },
    "ask_contact": {
        "es": "¿Qué contacto compartimos *solo si hay coincidencia y aceptas*? (ej. tu WhatsApp)",
        "en": "What contact should we share *only if there's a match and you agree*? (e.g. your WhatsApp)",
    },
    "ask_consent": {
        "es": "¿Autorizas compartir ese contacto con una coincidencia? Responde: si / no",
        "en": "Do you allow sharing that contact with a match? Reply: yes / no",
    },
    "money_warning": {
        "es": "⚠️ Seguridad: nunca envíes dinero por adelantado a desconocidos. Si te lo piden a cambio de ayuda, suele ser estafa.",
        "en": "⚠️ Safety: never send money up front to strangers. If someone asks for it in exchange for help, it's likely a scam.",
    },
    "high_risk_redirect": {
        "es": "Para alojamiento, dinero o casos con menores, es más seguro coordinar con una organización verificada que con desconocidos. Aquí tienes opciones:",
        "en": "For housing, money, or cases with minors, it's safer to coordinate with a verified organization than with strangers. Here are options:",
    },
    "saved_no_consent": {
        "es": "Guardé tu publicación sin compartir tu contacto. Escribe MENU para más opciones.",
        "en": "Saved your post without sharing your contact. Type MENU for more options.",
    },
    "saved_no_match": {
        "es": "✅ Registrado. Aún no hay coincidencias; te avisaremos cuando aparezca una.",
        "en": "✅ Registered. No matches yet; we'll notify you when one appears.",
    },
    "matches_header": {
        "es": "✅ ¡Posibles coincidencias! Contacta con cuidado:",
        "en": "✅ Possible matches! Reach out carefully:",
    },
    "browse_empty": {
        "es": "Por ahora no hay solicitudes abiertas en esa categoría. Escribe MENU.",
        "en": "No open requests in that category right now. Type MENU.",
    },
    "browse_header": {
        "es": "Solicitudes abiertas en la red:",
        "en": "Open requests in the network:",
    },
    "privacy": {
        "es": "Guardamos lo mínimo necesario. Escribe BORRAR para eliminar tus datos.",
        "en": "We store the minimum needed. Type DELETE to remove your data.",
    },
    "more_options": {
        "es": "— Escribe MENU para ver más opciones.",
        "en": "— Type MENU for more options.",
    },
    "mark_safe": {
        "es": "Qué alegría 🙏 Actualiza su estado en el registro donde fue reportada (Venezuela Te Busca o Desaparecidos Terremoto Venezuela), o avisa por la Cruz Roja: https://familylinks.icrc.org",
        "en": "Wonderful 🙏 Update their status in the registry where they were reported (Venezuela Te Busca or Desaparecidos Terremoto Venezuela), or notify the Red Cross: https://familylinks.icrc.org",
    },
    "authoritative_handoff": {
        "es": "Para la búsqueda oficial de familiares usa la Cruz Roja: https://familylinks.icrc.org",
        "en": "For the official family search use the Red Cross: https://familylinks.icrc.org",
    },
    "lang_set": {
        "es": "Idioma actualizado a Español. ✅",
        "en": "Language set to English. ✅",
    },
    "invalid": {
        "es": "No entendí. Escribe MENU para ver las opciones.",
        "en": "I didn't get that. Type MENU to see options.",
    },
}


def t(lang: str, key: str) -> str:
    s = STR.get(key, {"es": "", "en": ""})
    if lang == "en":
        return s["en"]
    if lang == "both":
        return s["es"] + "\n— — —\n" + s["en"]
    return s["es"]
