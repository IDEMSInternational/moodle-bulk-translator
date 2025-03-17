from abc import ABC, abstractmethod

from bs4 import BeautifulSoup
import bs4

from extract import (
    extract_content,
    preprocess_castext,
    standardize_content,
)


class TranslatableContentElement(ABC):

    @abstractmethod
    def __init__(self, xmlelement):
        '''Should define self.element and self.text'''
        pass

    @abstractmethod
    def replace_content_with(self, text):
        '''mutate self.element by replacing its contained content with `text`'''
        pass

    @abstractmethod
    def extract_content(self, language='en'):
        '''Return a list of text pieces that are contained in the element's text
        and that are suitable for translation'''
        pass

    @abstractmethod
    def generate_multilang(self, text: str, translation: dict) -> str:
        '''Generate a multi-language version of `text` using the `translation`
        dictionary. This uses Moodle or STACK specific tags to represent content
        in different languages.'''
        pass

    def replace_text_pieces(self, texts, translations, target_lang, source_lang='en'):
        '''mutate self.element by replacing each text piece from `texts` occurring
        in the element with a translated or multi-language version.'''

        # In order to deal with translation strings that may be
        # substrings of some other translation strings, we go in
        # order of decreasing length and use placeholders.
        html = self.text
        # Remove single digits from the dictionary, as our placeholders can't cope
        texts = [t for t in texts if t not in list("0123456789")]
        # do text replacements in decreasing order of length
        texts = sorted(set(texts), key=lambda t: len(t), reverse=True)
        placeholders = {}
        for i, text in enumerate(texts):
            # replace text with a placeholder
            placeholder = '\1' + '\1'.join(list(f"{i:>04}")) + '\1'
            placeholders[text] = placeholder
            html = html.replace(text, placeholder)
        # replace placeholder with multi-lang content
        for text in texts:
            placeholder = placeholders[text]
            translation = translations[text]
            multilang = self.generate_multilang(text, translation, target_lang, source_lang)
            multilang = multilang.replace("\xa0", "&nbsp;")
            html = html.replace(placeholder, multilang)
        # html = self.postprocess_castext(html)
        html = html.replace("\xa0", "&nbsp;")
        html = html.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        self.replace_content_with(html)


class CourseContentElement(TranslatableContentElement):
    '''Element in a Moodle course export'''

    def __init__(self, xmlelement):
        self.element = xmlelement
        self.text = standardize_content(xmlelement.text)

    def replace_content_with(self, text):
        self.element.string.replace_with(text)


class QBankContentElement(TranslatableContentElement):
    '''Element in a Moodle XML question bank export'''

    def __init__(self, xmlelement):
        self.element = xmlelement
        self.text = standardize_content(xmlelement.find('text').text)

    def replace_content_with(self, text):
        children = list(self.element.find('text').children)
        if children:
            if isinstance(children[0], bs4.element.CData) or isinstance(children[0], bs4.element.NavigableString):
                children[0].string.replace_with(text)
            else:
                print(f"Warning: strange text element {self.element}")


class HTMLTextElement(TranslatableContentElement):
    '''XML element containing plain text/html'''

    def extract_content(self, language='en'):
        return extract_content(self.text)

    def generate_multilang(self, text, translation, target_lang, source_lang):
        return f"{{mlang {source_lang}}}{text}{{mlang}}{{mlang {target_lang}}}{translation}{{mlang}}"


class STACKTextElement(TranslatableContentElement):
    '''XML element containing CasText'''

    '''This type of TextElement needs to preprocess the translations.
    So that it doesn't have to be done for every single call of replace_text_pieces,
    we cache the result of the first time replace_text_pieces is called, and store it
    in this singleton attribute.'''
    translations = {}

    def reset_translations():
        STACKTextElement.translations = {}

    def extract_content(self, language='en'):
        text = preprocess_castext(self.text)
        return extract_content(text)

    def generate_multilang(self, text, translation, target_lang, source_lang):
        # return f"[[lang code='en,other']]{text}[[/lang]][[lang code='fr']]{translation}[[/lang]]"
        return f"{{mlang {source_lang}}}{text}{{mlang}}{{mlang {target_lang}}}{translation}{{mlang}}"

    def replace_text_pieces(self, texts, translations, target_lang, source_lang='en'):
        if not STACKTextElement.translations:
            for src, trs in translations.items():
                src = src.replace("<x>", "").replace("</x>", "")
                trs = trs.replace("<x>", "").replace("</x>", "")
                CourseSTACKTextElement.translations[src] = trs
        texts = [t.replace("<x>", "").replace("</x>", "") for t in texts]
        super().replace_text_pieces(texts, STACKTextElement.translations, target_lang, source_lang)


class MaximaTextElement(TranslatableContentElement):
    '''XML element containing plain Maxima code (i.e. question/feedback variables)'''

    def __init__(self, xmlelement):
        raise NotImplementedError


class CourseHTMLTextElement(CourseContentElement, HTMLTextElement):
    pass


class CourseSTACKTextElement(CourseContentElement, STACKTextElement):
    pass


class CourseMaximaTextElement(CourseContentElement, MaximaTextElement):
    pass


class QBankHTMLTextElement(QBankContentElement, HTMLTextElement):
    pass


class QBankSTACKTextElement(QBankContentElement, STACKTextElement):
    pass


class QBankMaximaTextElement(QBankContentElement, MaximaTextElement):
    pass
