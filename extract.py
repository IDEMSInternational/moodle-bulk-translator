import re
import string

from bs4 import BeautifulSoup
import bs4

'''
May contain &lt; &gt; &amp; (escaped HTML) which needs to be converted.

Take text verbatim as long as it contains only:
    Text formatting: "b", "i", "u", "strong", "em", "mark", "small", "del", "ins", "sub", "sup"
    Links/media: "a", "img", "audio", "video"
    Section division?: "span", "div"?
    and its text is not only whitespace.

Otherwise, take only pieces of text that are directly within
this element, and recurse into all other elements that are
none of the above nor:
    script
    style

Any identified text pieces should also be split by
    <br>/<hr>, double newline
'''

FORMATTING_TAGS = [
    "b", "i", "u", "strong", "em", "mark", "small", "del", "ins", "sub", "sup",
    "a", "img", "audio", "video",
    "x", # Tag inserted to indicate content should not get translated
]
EXCLUDED_TAGS = [
    "script", "style",
    "jsxgraph", "jsstring", "comment", "todo", "geogebra", "parsons",  # STACK
    "debug", "include", "define", "commonstring", "pfs",  # STACK
]


def preprocess_castext(html):
    '''
    This takes STACK CASText and removes blocks that are irrelevant for translation,
    protects embedded maths from being mangled by translation by adding <x> tags around them,
    and turns STACK blocks into HTML tags. After this, we can use the standard text extraction
    function to get translatable texts.

    Blocks:
        - elif/else blocks need to be split into [[/if]][[if]]
        - Split/Strip [[input:ans1]] [[validation:ans1]] [[feedback:prt]] [[facts:name]]
        - Omit content within [[jsxgraph]], [[jsstring]], [[comment]], [[todo]], [[geogebra]], [[parsons]] blocks
        - Omit [[ debug /]], [[include src="..."/]], [[define src="..."/]], [[commonstring/]], [[pfs/]] block
        - process (treat like HTML tags): [[template]], [[if]], [[foreach]] [[moodleformat]], [[markdownformat]], [[htmlformat]], [[reveal]], [[hint]]
    LaTeX:
        Split string by \[\] and omit content within \[\].
        Treat \(\) and {@ @} as inline, let it be part of text (wrap into exclude translation html tag?)
        (unless at the beginning/end of text mod whitespace/punctuation).
    '''

    # Replace elif/else so they can be treated like HTML tags
    html = re.sub(r'\[\[\s*(else|elif)[^\[\]]*\]\]', '[[/if]][[if]]', html)
    # Remove input/etc fields, and put a break to make sure text gets split
    html = re.sub(r'\[\[\s*(input|validation|feedback|facts)[^\[\]]*\]\]', '<br/>', html)
    # Turn remaining STACK tags into HTML tags
    html = re.sub(r'\[\[\s*', '<', html).replace("]]", ">")
    # Remove big maths blocks, and put a break to make sure text gets split
    html = re.sub(r'\\\[[^\[\]]*\\\]', '<br/>', html)
    # Protect {@ @} and \( \) content from getting altered by translation
    html = html.replace("{#", "<x>{#").replace("#}", "#}</x>")
    html = html.replace("{@", "<x>{@").replace("@}", "@}</x>")
    html = html.replace("\\(", "<x>\\(").replace("\\)", "\\)</x>")
    # Remove nested <x> tags for clarity
    return remove_nested_tags(html)


def segment_by_tag(html):
    spans = [(m.start(), m.end()) for m in re.finditer('(<x>|</x>)', html)]
    segments = []
    lastpos = 0
    for span in spans:
        segments.append(html[lastpos:span[0]])
        segments.append(html[span[0]:span[1]])
        lastpos = span[1]
    segments.append(html[lastpos:])
    return segments


def remove_nested_tags(html):
    segments = segment_by_tag(html)

    new_segments = []
    depth = 0
    for segment in segments:
        if segment == "<x>":
            if depth == 0:
                new_segments.append(segment)
            depth += 1
        elif segment == "</x>":
            depth -= 1
            if depth == 0:
                new_segments.append(segment)
        else:
            new_segments.append(segment)

    return ''.join(new_segments)


def standardize_content(html):

    # This simplified solution changes the original formatting,
    # and all linebreaks are lost. We could use .prettify(),
    # but then we get a lot of extraneous linebreaks
    # html = html.replace("&amp;", "&amp;amp;").replace("&lt;", "&amp;lt;").replace("&gt;", "&amp;gt;")
    return str(BeautifulSoup(html, features="html.parser"))


def standardize_content_partial(html):
    '''
    This method is necessary because extract_content may change the order of
    attributes within a tag.

    In most cases, this yields the same as soup.text, but there are subtle differences.
    e.g. the input to extract_content is <a href="..." download="">
    but the output in the translatable string is <a download="" href="...">

    We can't simply do
    return str(BeautifulSoup(html, features="html.parser"))
    because that escapes < and > characters that are e.g. in Javascript code
    turing them into &lt; and &gt;
    '''

    # Find opening html tags with at least one attribute
    attr_tags = re.findall(r'<[A-Za-z]+[A-Za-z0-9]*\s+.+?>', html)
    for tag in set(attr_tags):
        # Convert to BS and back to string to get canonical attribute order
        std = str(BeautifulSoup(tag, features="html.parser"))
        # BS inserts a closing tag, remove that.
        std = re.sub(r"</[A-Za-z]+[A-Za-z0-9]*>", "", std)
        # Replace instance in html with canonical version
        html = html.replace(tag, std)
    # remove leading whitespace in front of closing tags
    html = re.sub(r"^[ \t]+</", "</", html, flags=re.MULTILINE)
    # html = html.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return html.replace("&nbsp;", "\xa0")


def extract_content(orig, language='en'):
    soup = BeautifulSoup(orig, features="html.parser")
    texts = _extract_texts(soup)
    validate_extraction(orig, texts)
    return [t for t in texts if len(t) >= 5]


def _extract_texts(element):
    if element.name in EXCLUDED_TAGS:
        return []
    if not element.text.strip(string.whitespace + '\xa0'):
        return []
    last_piece = ""
    texts = []
    for e in element.children:
        if isinstance(e, bs4.element.Comment):
            last_piece = last_piece.strip(string.whitespace + '\xa0')
            if last_piece:
                texts.append(last_piece)
            last_piece = ""
        elif e.name is None:
            last_piece += e.output_ready()  # ensure &lt; etc doesn't get converted
        # elif e.name == 'x':
        #     last_piece += f"<x>{e.text}</x>"
        elif _is_formatted_text(e):
            last_piece += str(e)
        else:
            last_piece = last_piece.strip(string.whitespace + '\xa0')
            if last_piece:
                texts.append(last_piece)
            last_piece = ""
            texts += _extract_texts(e)
    last_piece = last_piece.strip(string.whitespace + '\xa0')
    if last_piece:
        texts.append(last_piece)
    return texts


def _is_formatted_text(element):
    if element.name not in FORMATTING_TAGS:
        return False
    for child in element.findChildren():
        if isinstance(child, bs4.element.Comment):
            return False
        if isinstance(child, bs4.element.Tag) and child.name not in FORMATTING_TAGS:
            return False
    return True


def validate_extraction(orig, texts):
    '''
    All extracted strings should be substrings of the original text.
    If some extracted translation string is NOT a substring
    of the standardized element content, print out the offending content.
    '''
    html = standardize_content(orig)
    for text in texts:
        if html.find(text) == -1:
            print("================================")
            print(text)
            print("=== not found in ===")
            print(html)
