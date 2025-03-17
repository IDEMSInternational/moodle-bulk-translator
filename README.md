# Moodle bulk translator

Translate Moodle course exports and question banks using the DeepL API.

This tool is still work in progress and we aim to make its usage more streamlined.

The input content is assumed to be mono-lingual, i.e. without use of language blocks.
The output will be bilingual, using the multilang V2 filter (`{mlang en}...{mlang}` syntax).

Text content is assumed to be in plain text or HTML format. Titles/labels of sections as well as activities of the types page, label, quiz, resource and forum are extracted and translated. Questions of types STACK, multichoice and cloze are processed. STACK question variables are not affects, so in particular, multiple choice options and Parson's block content is currently not translated.

## Usage

You will first need to create a DeepL account, retrieve your [auth key](https://support.deepl.com/hc/en-us/articles/360020695820-API-Key-for-DeepL-s-API), and save it in `auth_key.json` in the format:

```
{
	"auth_key": "<your key here>"
}
```

This tool is written in python. You'll need to install its dependencies (in particular the DeepL API python library):

```
pip install -r requirements.txt
```

To translate an entire course:

- Export (backup) the course from Moodle and download the generated `.mbz` file
- Extract the content of the `.mbz` file into a folder (you may have to change the file extension to `.zip` beforehand)
- Call `translate_course` from `run.py` in a python script with the appropriate parameters

To translate a question bank:

- Export the question bank as moodle XML.
- Call `translate_qbank` from `run.py` in a python script with the appropriate parameters

Arguments for `translate_course/translate_qbank`:

- `path/filepath`:
	- `path`: for course translation: path (folder) to the extracted `.mbz` content
	- `filepath`: for question bank translation: path of the `.xml` question bank export
- `strings_file`: a temporary `.json` file where extracted strings to be translated are stored
- `translations_file`: a temporary `.json` file where translated strings are stored
- `target_lang`: Two-letter language code: Language to translate the course into
- `source_lang`: (optional) Two-letter language code: Language the course is in, assumed to be 'EN' if not provided

Output question banks/course content is written to an `output/` folder. In the case of course content, you will need to pack it into a zip-archive and change the extension to `.mbz`

Note: If you want to change the translation filter to use in the output, modify the `generate_multilang` functions in `elements.py`.

## Design

The tool operates by first extracting translatable strings from the input, writing them into a json file. Then the automatic translation is invoked on the json file and its output with the translations written to another json file. We then iterate over the input files again, this time inserting the translations, and saving the output in a separate folder `output/`.

The tool goes through different files and looks for relevant XML fields (`filehandlers.py`). The content of these fields is classified into different types (`elements.py`), such as regular text or STACK CASText. Different types of elements have different ways of extracting translatable strings from them, and re-inserting translated strings.

## Issues

We use the BeautifulSoup library for XML and HTML parsing. One issue with this is that while we can parse the input, modify it and export it again, in the export process all whitespace formatting around the HTML tags gets lost. Output formatting options are either no linebreaks (making outputs hard to read, e.g. CASText), or prettified, meaning all kinds of text, even `<b>` get rendered on their own line.

Furthermore, all `<`, `>`, `&` are escaped with their HTML sequence, unless they are in a `<script>` tag. A ``[[jsxgraph]]`` tag is not recognized as a script tag, and thus by default, javascript code within a jsxgraph-block would be broken. We implement custom logic for these cases, however, it may not be entirely foolproof.

We implement a custom solution in `extract.py`, which, however, is not entirely foolproof.

When looking for translatable strings, we want to use BeautifulSoup's HTML parsing to subdivide the content into logical units, that can then be sent for translation. However, in order not to mess up too much formatting, when inserting translations into the output, we do a simple search and replace rather than parsing the entire content again. Some extracted content is slightly modified in the parsing process, however, such as the order of attributes and the types of quotes used in tags, e.g. `<a href='...' download="">` may become `<a download="" href="...">`, making search and replace fail. Thus we use standardization functions to work around this. The function `standardize_content` is currently in use, but `standardize_content_partial` has been used in the past as well. Both have their own issues.

Applying a search and replace across the entire text element (e.g. full question text) has further issues: If a phrase that has been identified for translation appears identically somewhere outside of a translatable context (e.g. within JSXGraph), the replacement of the phrase with the translation is still performed. To partially mitigate this, the minimum length of a translatable string is 5 characters. Still, this can cause major issues if e.g. "validation", "input" or "feedback" is a phrase for translation, as input/validation/feedback fields will be broken. Similarly, javascript variable names, if they are identical to a phase that has been identified for translation.

More work needs to be done to find a satisfying solution.

### Other minor issues

- STACK questions may not contain `<x>` html tags in their CASText (we use this tag to tell DeepL not to translate content inside it)
- Content with invalid syntax (e.g. opening HTML tag without closing tag, or `{@` without corresponding closing tag) may not get translated properly
- CDATA is stripped out and replaced with text with escaped special characters (`<`, `>`, `&`)
