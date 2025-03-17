from pathlib import Path
import os

from bs4 import BeautifulSoup

from elements import (
    QBankHTMLTextElement,
    QBankSTACKTextElement,
    CourseHTMLTextElement,
    CourseSTACKTextElement,
)


def elements_from_tag_tree_list(elements, tags):
    for tag in tags:
        elements = [c for e in elements for c in e.findChildren(tag, recursive=False)]
    return elements


def elements_from_tag_tree(soup, tags):
    elements = [soup]
    return elements_from_tag_tree_list(elements, tags)


class XMLFileHandler:
    def get_files(root):
        '''Returns a list of XML files to process for translation'''
        return []

    def get_translatable_elements(soup):
        '''Returns a list of TranslatableElements'''
        return []


class SectionXMLFileHandler(XMLFileHandler):
    def get_files(self, root):
        return root.glob("sections/section_*/section.xml")

    def get_translatable_elements(self, soup):
        elements = [
            soup.section.find('name'),
            soup.section.summary,
        ]
        return [CourseHTMLTextElement(e) for e in elements]


'''
<qtype> To infer which translation tags to use (multichoice/numerical/stack)
<name>
<questiontext>
<generalfeedback>
<plugin_qtype_stack_question>
    <stackoptions>
        <specificfeedback>
        <prtcorrect>
        <prtpartiallycorrect>
        <prtincorrect>
    <stackprts>
        <stackprt>
            <stackprtnodes>
                <stackprtnode>
                    <truefeedback>
                    <falsefeedback>
<plugin_qtype_multichoice_question>
    <answers>
        <answer>
            <answertext>
            <feedback>
'''

class QuestionsXMLFileHandler(XMLFileHandler):
    def get_files(self, root):
        return root.glob("questions.xml")

    def get_translatable_elements(self, soup):
        questions = elements_from_tag_tree(soup, [
            "question_categories",
            "question_category",
            "question_bank_entries",
            "question_bank_entry",
            "question_version",
            "question_versions",
            "questions",
            "question",
        ])
        return self.get_question_elements(questions) + self.get_stack_question_elements(questions)

    def get_common_question_elements(self, questions):
        return [
            e for q in questions for e in (
                # q.find('name'), 
                q.questiontext, 
                q.generalfeedback, 
            )
        ]

    def get_question_elements(self, questions):
        questions = [q for q in questions if q.qtype.text in ['multichoice', 'numerical']]
        elements = self.get_common_question_elements(questions)
        elements += elements_from_tag_tree_list(questions, [
            "plugin_qtype_multichoice_question",
            "answers",
            "answer",
            "answertext",
        ]) + elements_from_tag_tree_list(questions, [
            "plugin_qtype_multichoice_question",
            "answers",
            "answer",
            "feedback",
        ])
        return [CourseHTMLTextElement(e) for e in elements]

    def get_stack_question_elements(self, questions):
        questions = [q for q in questions if q.qtype.text == 'stack']
        elements = self.get_common_question_elements(questions)
        options = elements_from_tag_tree_list(questions, [
            "plugin_qtype_stack_question",
            "stackoptions",
        ])
        elements += [
            e for o in options for e in (
                o.specificfeedback, 
                o.prtcorrect, 
                o.prtpartiallycorrect, 
                o.prtincorrect, 
            )
        ]
        elements += elements_from_tag_tree_list(questions, [
            "plugin_qtype_stack_question",
            "stackprts",
            "stackprt",
            "stackprtnodes",
            "stackprtnode",
            "truefeedback",
        ]) + elements_from_tag_tree_list(questions, [
            "plugin_qtype_stack_question",
            "stackprts",
            "stackprt",
            "stackprtnodes",
            "stackprtnode",
            "falsefeedback",
        ])
        return [CourseSTACKTextElement(e) for e in elements]


'''
![CDATA[...]]
<quiz>
All fields have a <text> subfield.

<question type="category">
    ignore

<question type="stack">
    <name>
        <text>
    <questiontext format="html">
        <text>
    <generalfeedback format="html">
        <text>
    <questionvariables>
        <text>
    <specificfeedback format="html">
        <text>
    <prtcorrect format="html">
        <text>
    <prtpartiallycorrect format="html">
        <text>
    <prtincorrect format="html">
        <text>
    <prt>
        <feedbackvariables>
            <text>
        <node>
            <truefeedback format="html">
                <text>
            <falsefeedback format="html">
                <text>

<question type="cloze">
    <name>
        <text>
    <questiontext format="html">
        <text>
    <generalfeedback format="html">
        <text>

<question type="multichoice">
    <name>
        <text>
    <questiontext format="html">
        <text>
    <generalfeedback format="html">
        <text>
    <correctfeedback format="html">
        <text>
    <partiallycorrectfeedback format="html">
        <text>
    <incorrectfeedback format="html">
        <text>
    <answer fraction="100" format="html">
        <text>
        <feedback format="html">
            <text>
'''

class QBankXMLFileHandler(XMLFileHandler):
    def __init__(self, filename):
        self.filename = filename

    def get_files(self, root):
        return root.glob(self.filename)

    def get_translatable_elements(self, soup):
        questions = elements_from_tag_tree(soup, [
            "quiz",
            "question",
        ])
        return self.get_question_elements(questions) + self.get_stack_question_elements(questions)

    def get_question_elements(self, questions):
        mcq_questions = [q for q in questions if q["type"] == 'multichoice']
        cloze_questions = [q for q in questions if q["type"] == 'cloze']
        elements = [
            e for q in mcq_questions for e in (
                q.questiontext, 
                q.generalfeedback,
                q.correctfeedback, 
                q.partiallycorrectfeedback,
                q.incorrectfeedback,
            )
        ]
        elements += [
            e for q in cloze_questions for e in (
                q.questiontext, 
                q.generalfeedback,
            )
        ]
        answers = elements_from_tag_tree_list(questions, [
            "answer",
        ])
        elements += [
            e for o in answers for e in (
                o,
                o.feedback,
            )
        ]
        return [QBankHTMLTextElement(e) for e in elements]

    def get_stack_question_elements(self, questions):
        questions = [q for q in questions if q["type"] == 'stack']
        elements = [
            e for q in questions for e in (
                q.questiontext, 
                q.generalfeedback, 
                q.specificfeedback,
                q.prtcorrect,
                q.prtpartiallycorrect,
                q.prtincorrect,
            )
        ]
        prtnodes = elements_from_tag_tree_list(questions, [
            "prt",
            "node",
        ])
        elements += [
            e for o in prtnodes for e in (
                o.truefeedback,
                o.falsefeedback,
            )
        ]
        return [QBankSTACKTextElement(e) for e in elements]


class BackupXMLFileHandler(XMLFileHandler):
    def get_files(self, root):
        return root.glob("moodle_backup.xml")

    def get_translatable_elements(self, soup):
        elements = elements_from_tag_tree(soup, [
            "moodle_backup", 
            "information", 
            "contents", 
            "activities", 
            "activity", 
            "title",
        ])
        return [CourseHTMLTextElement(e) for e in elements]


class ActivityXMLFileHandler(XMLFileHandler):
    def __init__(self, activity_type):
        self.activity_type = activity_type

    def get_files(self, root):
        return root.glob(f"activities/{self.activity_type}_*/{self.activity_type}.xml")

    def get_translatable_elements(self, soup):
        elements = elements_from_tag_tree(soup, [
            "activity", 
            self.activity_type, 
            "name",
        ]) + elements_from_tag_tree(soup, [
            "activity", 
            self.activity_type, 
            "intro",
        ])
        return [CourseHTMLTextElement(e) for e in elements]


class PageActivityXMLFileHandler(ActivityXMLFileHandler):
    def __init__(self):
        self.activity_type = "page"

    def get_translatable_elements(self, soup):
        parent_elements = super().get_translatable_elements(soup)
        elements = elements_from_tag_tree(soup, [
            "activity", 
            self.activity_type, 
            "content",
        ])
        return parent_elements + [CourseHTMLTextElement(e) for e in elements]


def process_content(handlers, root, f_proc, write_output=False):
    '''
    f_proc is a processor function over all the translatable elements that
    were found in a file. It may mutate the elements, so that when we dump
    the soup into a new file, it contains the mutated elements.
    '''
    for fp in handlers:
        for path in fp.get_files(root):
            with open(path, "r") as f:
                # print(path)
                content = f.read()
                soup = BeautifulSoup(content, 'xml')
                elements = fp.get_translatable_elements(soup)
                f_proc(elements)
                if write_output:
                    dest = Path("output") / path
                    os.makedirs(dest.parent, exist_ok=True)
                    with open(dest, "w") as file:
                        file.write(str(soup))
