import json
from pathlib import Path

import deepl


def load_auth_key(filename):
    data = json.load(open(filename))
    return data["auth_key"]


class DeepLTranslator:
    def __init__(self, stringfile, translationfile, outputfile=None):
        '''
        stringfile: Strings to be translated (json flat dict)
        translationfile: Pre-existing translations (json flat dict)
        outputfile: Destination to write translations for strings to (json flat dict)
            If not provided, translationfile is updated with the new translations.
        '''
        with open(stringfile) as f:
            self.strings = json.load(f)
            self.cached_translations = {}
            trs_file = Path(translationfile)
            if trs_file.is_file():
                with open(trs_file) as f:
                    self.cached_translations = json.load(f)
            self.outputfile = outputfile or translationfile
            self.inplace = self.outputfile == translationfile

    def translate(self, **kwargs):
        auth_key = load_auth_key("auth_key.json")
        self.translator = deepl.Translator(auth_key)
        total = 0
        count = 0
        batch = []
        self.new_translations = {}
        for src, _ in self.strings.items():
            if src in self.cached_translations:
                self.new_translations[src] = self.cached_translations[src]
                continue
            if count < 49:
                batch.append(src)
                total += 1
                count += 1
            else:
                batch.append(src)
                total += 1
                self.translate_batch(batch, **kwargs)
                count = 0
                batch = []
        if batch:
            self.translate_batch(batch, **kwargs)
        print(f"Translated {total} new strings.")

    def translate_batch(self, batch, **kwargs):
        result = self.translator.translate_text(batch, **kwargs)
        batch_tr = [entry.text for entry in result]
        translations = {k:v for k,v in zip(batch, batch_tr)}
        self.new_translations.update(translations)
        self.cached_translations.update(translations)
        # Update outputfile with new batch of translations
        # We do this periodically as not to lose progress in case of a failure
        if self.inplace:
            with open(self.outputfile, "w") as f:
                json.dump(self.cached_translations, f, indent=4)
        else:
            with open(self.outputfile, "w") as f:
                json.dump(self.new_translations, f, indent=4)


if __name__ == "__main__":
    txt = "Una variabile aleatoria continua <x>\\(X\\)</x> ha la seguente funzione di densit\u00e0 di probabilit\u00e0:"
    auth_key = load_auth_key("auth_key.json")
    translator = deepl.Translator(auth_key)
    out = translator.translate_text([txt], target_lang="EN-US", source_lang="IT", tag_handling="xml", ignore_tags="x")
    print(out[0].text)
