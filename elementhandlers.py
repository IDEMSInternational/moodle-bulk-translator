import json

from bs4 import BeautifulSoup


class StringExporter:
    def __init__(self, source_lang='en'):
        self.strings = {}
        self.source_lang = source_lang

    def process(self, elements):
        for e in elements:
            texts = e.extract_content()
            for text in texts:
                self.strings[text] = None

    def write_strings(self, filename):
        with open(filename, "w") as f:
            json.dump(self.strings, f, indent=4)


class ElementTranslator:
    def __init__(self, translation_file, target_lang, source_lang='en'):
        with open(translation_file) as f:
            self.translations = json.load(f)
        self.target_lang = target_lang
        self.source_lang = source_lang

    def process(self, elements):
        for e in elements:
            self.translate_content(e)

    def translate_content(self, e):
        texts = e.extract_content()
        e.replace_text_pieces(texts, self.translations, self.target_lang, self.source_lang)
