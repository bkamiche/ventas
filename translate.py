import deepl
import polib
import shutil
import re

# Tu clave API de DeepL
auth_key = "14556c52-fdb0-4310-884a-327f6987f465:fx"
translator = deepl.Translator(auth_key)

files = [
    ('translations/en/LC_MESSAGES/messages.po', 'EN-US'),
    ('translations/pt/LC_MESSAGES/messages.po', 'PT-BR'),
    ('translations/de/LC_MESSAGES/messages.po', 'DE'),
    ('translations/it/LC_MESSAGES/messages.po', 'IT'),
    ('translations/fr/LC_MESSAGES/messages.po', 'FR'),
]

def reemplazar_placeholders(texto):
    """
    Busca las cadenas entre llaves y las reemplaza por marcadores temporales.
    Devuelve el texto modificado y un diccionario mapeando el marcador con el placeholder.
    """
    placeholders = re.findall(r'\{[^}]+\}', texto)
    marcador_dic = {}
    texto_mod = texto
    for i, ph in enumerate(placeholders):
        marcador = f"___PH{i}___"
        marcador_dic[marcador] = ph
        texto_mod = texto_mod.replace(ph, marcador)
    return texto_mod, marcador_dic

def restaurar_placeholders(texto, marcador_dic):
    """
    Restaura los marcadores a sus valores originales en el texto.
    """
    for marcador, ph in marcador_dic.items():
        texto = texto.replace(marcador, ph)
    return texto

for file in files:
    print("Procesando", file[0], "a", file[1])
    try:
        shutil.copy(file[0], file[0].replace('.po', '.po.old'))
    except Exception as e:
        print("Error al copiar archivo:", e)
        quit()
    po = polib.pofile(file[0])
    cambios = False
    for entry in po.untranslated_entries():
        print("Texto original:", entry.msgid)
        # Reemplazar los placeholders por marcadores temporales en el msgid
        texto_para_traducir, marcador_dic = reemplazar_placeholders(entry.msgid)
        # Traducir el texto sin los placeholders
        result = translator.translate_text(texto_para_traducir, target_lang=file[1], source_lang='ES')
        texto_traducido = result.text
        # Restaurar los placeholders en el texto traducido
        texto_final = restaurar_placeholders(texto_traducido, marcador_dic)
        print("Traducción:", texto_final)
        entry.msgstr = texto_final
        cambios = True
    if cambios:
        print("Actualizando archivo...")
        po.save(file[0])
quit()

# Archivo fuente (.po) y archivo traducido
input_file = 'messages.po'
output_file = 'messages_translated.po'
source_language = 'ES'
target_language = 'DE'  # Código de idioma objetivo

# Cargar archivo .po
po = polib.pofile(input_file)
# Traducir cadenas
for entry in po.untranslated_entries():
    result = translator.translate_text(entry.msgid, target_lang=file[1], source_language='ES')
    entry.msgstr = result.text
# Guardar archivo traducido
po.save(output_file)

print(f"Traducción completada. Guardado en {output_file}")
