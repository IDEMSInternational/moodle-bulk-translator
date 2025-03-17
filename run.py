from pathlib import Path

from elementhandlers import (
    ElementTranslator,
    StringExporter,
)
from deepltranslator import DeepLTranslator
from filehandlers import (
    SectionXMLFileHandler,
    ActivityXMLFileHandler,
    PageActivityXMLFileHandler,
    QuestionsXMLFileHandler,
    QBankXMLFileHandler,
    process_content,
)


def transform_lang_code(code):
    '''Take DeepL language code and change it to Moodle language code'''
    return code.split("-")[0].lower()


def translate_content(handlers, root, strings_file, translations_file, target_lang, source_lang='EN-US'):
    bse = StringExporter(source_lang=transform_lang_code(source_lang))
    process_content(handlers, root, bse.process)
    bse.write_strings(strings_file)

    translator = DeepLTranslator(strings_file, translations_file)
    translator.translate(target_lang=target_lang, source_lang=source_lang, tag_handling="xml", ignore_tags="x")

    bet = ElementTranslator(translations_file, target_lang=transform_lang_code(target_lang), source_lang=transform_lang_code(source_lang))
    process_content(handlers, root, bet.process, write_output=True)


def translate_course(path, strings_file, translations_file, target_lang, source_lang='EN'):
    handlers = [
        SectionXMLFileHandler(),
        # BackupXMLFileHandler(),    # Abbreviated stuff: can be ignored?
        ActivityXMLFileHandler("label"),
        ActivityXMLFileHandler("quiz"),
        ActivityXMLFileHandler("resource"),
        ActivityXMLFileHandler("forum"),
        PageActivityXMLFileHandler(),
        QuestionsXMLFileHandler(),
    ]
    root = Path(path)
    translate_content(handlers, root, strings_file, translations_file, target_lang, source_lang)


def translate_qbank(filepath, strings_file, translations_file, target_lang, source_lang='EN'):
    handlers = [
        QBankXMLFileHandler(filepath),
    ]
    root = Path(".")
    translate_content(handlers, root, strings_file, translations_file, target_lang, source_lang)


# translate_course("content", "strings.json", "translations.json", "FR")
# translate_qbank("qbank.xml", "strings_qb.json", "translations_qb.json", "FR")
# translate_qbank("alg_italian.xml", "strings_imm.json", "translations_imm.json", "EN-US", "IT")
translate_qbank("pak_italian.xml", "strings_imm.json", "translations_imm.json", "EN-US", "IT")
