# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import xml.etree.cElementTree as ET
from zipfile import ZipFile
from os import path, makedirs
from django.conf import settings
from bs4 import BeautifulSoup
import re
from api.models import (
    QuestionLibrary, Section, Question,
    MultipleChoice, MultipleChoiceAnswer,
    TrueFalse, Fib, MultipleSelect, MultipleSelectAnswer,
    Matching, MatchingChoice, MatchingAnswer,
    Ordering, WrittenResponse
)
from api.models import (
    QuestionLibrary, Section, Question,
    MultipleChoice, MultipleChoiceAnswer,
    TrueFalse, Fib, MultipleSelect, MultipleSelectAnswer,
    Matching, MatchingChoice, MatchingAnswer,
    Ordering, WrittenResponse
)


class XmlReader:
    """
    Reads and parses SCORM XML files (questiondb.xml, imsmanifest.xml)
    and extracts data into Django models.
    This class mirrors the structure of XmlWriter but in reverse.
    """
    
    def __init__(self, scorm_zip_path, extract_to_path=None):
        """
        Initialize XmlReader with a SCORM ZIP file path.
        
        Args:
            scorm_zip_path: Path to the SCORM ZIP file
            extract_to_path: Optional path to extract ZIP contents (defaults to temp directory)
        """
        self.scorm_zip_path = scorm_zip_path
        self.extract_to_path = extract_to_path
        self.questiondb_xml = None
        self.imsmanifest_xml = None
        self.extracted_path = None
        
        # Extract ZIP file
        self._extract_zip()
        
        # Parse XML files
        self._parse_xml_files()
    
    def _extract_zip(self):
        """Extract SCORM ZIP file to temporary directory."""
        if not path.exists(self.scorm_zip_path):
            raise FileNotFoundError(f"SCORM ZIP file not found: {self.scorm_zip_path}")
        
        # Create extraction directory if not provided
        if self.extract_to_path is None:
            # Use a temp directory based on the ZIP filename
            zip_basename = path.splitext(path.basename(self.scorm_zip_path))[0]
            self.extract_to_path = path.join(settings.MEDIA_ROOT, f"scorm_extract_{zip_basename}")
        
        # Create directory if it doesn't exist
        if not path.exists(self.extract_to_path):
            makedirs(self.extract_to_path)
        
        # Extract ZIP file
        with ZipFile(self.scorm_zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.extract_to_path)
        
        self.extracted_path = self.extract_to_path
    
    def _parse_xml_files(self):
        """Parse questiondb.xml and imsmanifest.xml from extracted files."""
        questiondb_path = path.join(self.extracted_path, "questiondb.xml")
        imsmanifest_path = path.join(self.extracted_path, "imsmanifest.xml")
        
        if not path.exists(questiondb_path):
            raise FileNotFoundError(f"questiondb.xml not found in SCORM package: {questiondb_path}")
        
        if not path.exists(imsmanifest_path):
            raise FileNotFoundError(f"imsmanifest.xml not found in SCORM package: {imsmanifest_path}")
        
        # Parse XML files
        self.questiondb_xml = ET.parse(questiondb_path)
        self.imsmanifest_xml = ET.parse(imsmanifest_path)
    
    def parse_manifest(self):
        """
        Parse imsmanifest.xml and extract metadata.
        
        Returns:
            dict: Dictionary containing manifest metadata
        """
        root = self.imsmanifest_xml.getroot()
        
        manifest_data = {
            'identifier': root.get('identifier', ''),
            'resources': []
        }
        
        # Parse resources
        resources_el = root.find('resources')
        if resources_el is not None:
            for resource_el in resources_el.findall('resource'):
                resource_data = {
                    'identifier': resource_el.get('identifier', ''),
                    'type': resource_el.get('type', ''),
                    'material_type': resource_el.get('{http://desire2learn.com/xsd/d2lcp_v2p0}material_type', ''),
                    'href': resource_el.get('href', ''),
                    'link_target': resource_el.get('{http://desire2learn.com/xsd/d2lcp_v2p0}link_target', ''),
                    'title': resource_el.get('title', '')
                }
                manifest_data['resources'].append(resource_data)
        
        return manifest_data
    
    def parse_questiondb(self):
        """
        Parse questiondb.xml and extract question library structure.
        
        Returns:
            dict: Dictionary containing question library data structure
        """
        root = self.questiondb_xml.getroot()
        
        # Find objectbank element
        objectbank_el = root.find('objectbank')
        if objectbank_el is None:
            raise ValueError("objectbank element not found in questiondb.xml")
        
        question_library_data = {
            'ident': objectbank_el.get('ident', ''),
            'sections': []
        }
        
        # Parse base section (root section)
        base_sections = objectbank_el.findall('section')
        for section_el in base_sections:
            section_data = self._parse_section(section_el)
            question_library_data['sections'].append(section_data)
        
        return question_library_data
    
    def _parse_section(self, section_el):
        """
        Parse a section element and extract section data.
        
        Args:
            section_el: XML element representing a section
            
        Returns:
            dict: Dictionary containing section data
        """
        section_data = {
            'ident': section_el.get('ident', ''),
            'title': section_el.get('title', ''),
            'shuffle': False,
            'is_title_displayed': True,
            'is_text_displayed': False,
            'text': '',
            'questions': []
        }
        
        # Check for shuffle (selection_ordering with Random order)
        selection_ordering = section_el.find('selection_ordering')
        if selection_ordering is not None:
            order_el = selection_ordering.find('order')
            if order_el is not None and order_el.get('order_type') == 'Random':
                section_data['shuffle'] = True
        
        # Parse presentation material (section text)
        presentation_material = section_el.find('presentation_material')
        if presentation_material is not None:
            text = self._extract_text_from_material(presentation_material)
            section_data['text'] = text
        
        # Parse sectionproc_extension
        sectionproc = section_el.find('sectionproc_extension')
        if sectionproc is not None:
            display_name = sectionproc.find('{http://desire2learn.com/xsd/d2lcp_v2p0}display_section_name')
            if display_name is not None:
                section_data['is_title_displayed'] = display_name.text.lower() == 'yes'
            
            type_display = sectionproc.find('{http://desire2learn.com/xsd/d2lcp_v2p0}type_display_section')
            if type_display is not None:
                section_data['is_text_displayed'] = type_display.text == '1'
        
        # Parse nested sections
        nested_sections = section_el.findall('section')
        for nested_section_el in nested_sections:
            nested_section_data = self._parse_section(nested_section_el)
            section_data['sections'] = section_data.get('sections', [])
            section_data['sections'].append(nested_section_data)
        
        # Parse questions (items)
        items = section_el.findall('item')
        for item_el in items:
            question_data = self._parse_question(item_el)
            section_data['questions'].append(question_data)
        
        return section_data
    
    def _parse_question(self, item_el):
        """
        Parse a question (item) element and extract question data.
        
        Args:
            item_el: XML element representing a question item
            
        Returns:
            dict: Dictionary containing question data
        """
        question_data = {
            'ident': item_el.get('ident', ''),
            'label': item_el.get('label', ''),
            'title': item_el.get('title', ''),
            'question_type': None,
            'points': 1.0,
            'text': '',
            'hint': None,
            'feedback': None,
            'question_specific_data': {}
        }
        
        # Parse itemmetadata to get question type and points
        itemmetadata = item_el.find('itemmetadata')
        if itemmetadata is not None:
            qtidata = itemmetadata.find('qtimetadata')
            if qtidata is not None:
                for field in qtidata.findall('qti_metadatafield'):
                    fieldlabel = field.find('fieldlabel')
                    fieldentry = field.find('fieldentry')
                    if fieldlabel is not None and fieldentry is not None:
                        if fieldlabel.text == 'qmd_questiontype':
                            question_data['question_type'] = fieldentry.text
                        elif fieldlabel.text == 'qmd_weighting':
                            try:
                                question_data['points'] = float(fieldentry.text)
                            except (ValueError, TypeError):
                                pass
        
        # Parse presentation to get question text
        presentation = item_el.find('presentation')
        if presentation is not None:
            question_text = self._extract_question_text(presentation)
            question_data['text'] = question_text
        
        # Parse hint
        hint_el = item_el.find('hint')
        if hint_el is not None:
            question_data['hint'] = self._extract_text_from_hint(hint_el)
        
        # Parse general feedback
        feedback_els = item_el.findall('itemfeedback')
        for feedback_el in feedback_els:
            # General feedback typically has ident matching the question label
            if feedback_el.get('ident') == question_data['label']:
                question_data['feedback'] = self._extract_text_from_feedback(feedback_el)
        
        # Parse question-specific data based on type
        question_type = question_data['question_type']
        if question_type:
            if question_type == 'Multiple Choice':
                question_data['question_specific_data'] = self._parse_multiple_choice(item_el, question_data['label'])
                question_data['question_type_code'] = 'MC'
            elif question_type == 'True/False':
                question_data['question_specific_data'] = self._parse_true_false(item_el, question_data['label'])
                question_data['question_type_code'] = 'TF'
            elif question_type == 'Fill in the Blanks':
                question_data['question_specific_data'] = self._parse_fill_in_the_blanks(item_el, question_data['label'])
                question_data['question_type_code'] = 'FIB'
            elif question_type == 'Multi-Select':
                question_data['question_specific_data'] = self._parse_multi_select(item_el, question_data['label'])
                question_data['question_type_code'] = 'MS'
            elif question_type == 'Matching':
                question_data['question_specific_data'] = self._parse_matching(item_el, question_data['label'])
                question_data['question_type_code'] = 'MAT'
            elif question_type == 'Ordering':
                question_data['question_specific_data'] = self._parse_ordering(item_el, question_data['label'])
                question_data['question_type_code'] = 'ORD'
            elif question_type == 'Long Answer':
                question_data['question_specific_data'] = self._parse_written_response(item_el, question_data['label'])
                question_data['question_type_code'] = 'WR'
        
        return question_data
    
    def _extract_text_from_material(self, material_el):
        """
        Extract text content from material element, handling CDATA.
        Automatically cleans CDATA whitespace and HTML tags.
        """
        text_parts = []
        
        # Navigate through flow_mat -> material -> mattext
        flow_mat = material_el.find('flow_mat')
        if flow_mat is not None:
            materials = flow_mat.findall('.//material')
            for material in materials:
                mattext = material.find('mattext')
                if mattext is not None:
                    # Get text content (handles CDATA)
                    raw_text = mattext.text if mattext.text else ''
                    # Also check for CDATA in tail
                    if mattext.tail:
                        raw_text += mattext.tail
                    # Clean CDATA whitespace while preserving HTML tags
                    cleaned_text = self._clean_cdata_text(raw_text)
                    text_parts.append(cleaned_text)
        
        return ''.join(text_parts)
    
    def _extract_question_text(self, presentation_el):
        """
        Extract question text from presentation element.
        Automatically cleans CDATA whitespace and HTML tags.
        """
        text_parts = []
        
        flow = presentation_el.find('flow')
        if flow is not None:
            # Find first material element (question text)
            material = flow.find('material')
            if material is not None:
                mattext = material.find('mattext')
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ''
                    if mattext.tail:
                        raw_text += mattext.tail
                    # Clean CDATA whitespace while preserving HTML tags
                    cleaned_text = self._clean_cdata_text(raw_text)
                    text_parts.append(cleaned_text)
        
        return ''.join(text_parts)
    
    def _extract_text_from_hint(self, hint_el):
        """Extract text from hint element."""
        hintmaterial = hint_el.find('hintmaterial')
        if hintmaterial is not None:
            return self._extract_text_from_material(hintmaterial)
        return None
    
    def _extract_text_from_feedback(self, feedback_el):
        """
        Extract text from feedback element.
        Automatically cleans CDATA whitespace while preserving HTML tags.
        """
        material = feedback_el.find('material')
        if material is not None:
            mattext = material.find('mattext')
            if mattext is not None:
                raw_text = mattext.text if mattext.text else ''
                # Clean CDATA whitespace while preserving HTML tags
                return self._clean_cdata_text(raw_text)
        return None
    
    def _clean_cdata_text(self, text):
        """
        Clean text extracted from CDATA sections in SCORM XML.
        
        SCORM XML often contains CDATA with excessive whitespace, newlines, and tabs
        that are formatting artifacts rather than meaningful content. This method:
        1. Preserves HTML tags (e.g., <p>, <strong>, etc.)
        2. Normalizes whitespace between HTML tags (multiple spaces/newlines/tabs -> single space)
        3. Trims leading/trailing whitespace
        
        This ensures clean JSON output while preserving HTML structure for proper rendering.
        
        Args:
            text: Raw text string from XML CDATA
            
        Returns:
            str: Cleaned text with normalized whitespace but HTML tags preserved
        """
        if not text:
            return ''
        
        try:
            # Normalize whitespace while preserving HTML tags
            # Replace sequences of whitespace (spaces, tabs, newlines) with a single space
            # But be careful not to break HTML tag structure
            cleaned = re.sub(r'[ \t\n\r]+', ' ', text)
            # Remove whitespace between HTML tags (e.g., "> <" -> "><")
            cleaned = re.sub(r'>\s+<', '><', cleaned)
            # Trim leading/trailing whitespace
            cleaned = cleaned.strip()
            return cleaned
        except Exception:
            # Fallback: if regex fails, just normalize whitespace
            cleaned = re.sub(r'\s+', ' ', text).strip()
            return cleaned
    
    def _parse_multiple_choice(self, item_el, question_ident):
        """
        Parse multiple choice question data.
        Mirrors generate_multiple_choice() from XmlWriter.
        """
        mc_data = {
            'randomize': False,
            'enumeration': 4,
            'answers': []
        }
        
        presentation = item_el.find('presentation')
        if presentation is None:
            return mc_data
        
        flow = presentation.find('flow')
        if flow is None:
            return mc_data
        
        # Parse response_extension for enumeration
        response_ext = flow.find('response_extension')
        if response_ext is not None:
            enumeration_el = response_ext.find('{http://desire2learn.com/xsd/d2lcp_v2p0}enumeration')
            if enumeration_el is not None and enumeration_el.text:
                try:
                    mc_data['enumeration'] = int(enumeration_el.text)
                except (ValueError, TypeError):
                    pass
        
        # Parse response_lid for answers
        response_lid = flow.find('response_lid')
        if response_lid is not None:
            # Check shuffle setting
            render_choice = response_lid.find('render_choice')
            if render_choice is not None:
                mc_data['randomize'] = render_choice.get('shuffle', 'no').lower() == 'yes'
            
            # Parse answer options
            question_lid = response_lid.get('ident', '')
            answer_index = 1
            for flow_label in response_lid.findall('.//flow_label'):
                response_label = flow_label.find('response_label')
                if response_label is not None:
                    answer_ident = response_label.get('ident', '')
                    # Extract answer text
                    mattext = response_label.find('.//mattext')
                    answer_text = ''
                    if mattext is not None:
                        raw_text = mattext.text if mattext.text else ''
                        # Clean CDATA whitespace while preserving HTML tags
                        answer_text = self._clean_cdata_text(raw_text)
                    
                    # Find weight from resprocessing
                    weight = 0.0
                    answer_feedback = None
                    resprocessing = item_el.find('resprocessing')
                    if resprocessing is not None:
                        for respcondition in resprocessing.findall('respcondition'):
                            conditionvar = respcondition.find('conditionvar')
                            if conditionvar is not None:
                                varequal = conditionvar.find('varequal')
                                if varequal is not None and varequal.get('respident') == question_lid:
                                    if varequal.text == answer_ident:
                                        setvar = respcondition.find('setvar')
                                        if setvar is not None:
                                            try:
                                                weight = float(setvar.text)
                                            except (ValueError, TypeError):
                                                pass
                                        
                                        # Find answer-specific feedback
                                        displayfeedback = respcondition.find('displayfeedback')
                                        if displayfeedback is not None:
                                            feedback_ident = displayfeedback.get('linkrefid', '')
                                            feedback_el = item_el.find(f".//itemfeedback[@ident='{feedback_ident}']")
                                            if feedback_el is not None:
                                                answer_feedback = self._extract_text_from_feedback(feedback_el)
                    
                    mc_data['answers'].append({
                        'answer': answer_text,
                        'weight': weight,
                        'answer_feedback': answer_feedback,
                        'order': answer_index
                    })
                    answer_index += 1
        
        return mc_data
    
    def _parse_true_false(self, item_el, question_ident):
        """
        Parse true/false question data.
        Mirrors generate_true_false() from XmlWriter.
        """
        tf_data = {
            'true_weight': 0.0,
            'true_feedback': None,
            'false_weight': 0.0,
            'false_feedback': None,
            'enumeration': 4
        }
        
        presentation = item_el.find('presentation')
        if presentation is None:
            return tf_data
        
        flow = presentation.find('flow')
        if flow is None:
            return tf_data
        
        # Parse response_extension for enumeration
        response_ext = flow.find('response_extension')
        if response_ext is not None:
            enumeration_el = response_ext.find('{http://desire2learn.com/xsd/d2lcp_v2p0}enumeration')
            if enumeration_el is not None and enumeration_el.text:
                try:
                    tf_data['enumeration'] = int(enumeration_el.text)
                except (ValueError, TypeError):
                    pass
        
        # Parse response_lid for True/False options
        response_lid = flow.find('response_lid')
        if response_lid is not None:
            question_lid = response_lid.get('ident', '')
            
            # Get the order of True/False options from response labels
            # First response_label is True, second is False
            render_choice = response_lid.find('render_choice')
            true_ident = None
            false_ident = None
            if render_choice is not None:
                response_labels = render_choice.findall('.//response_label')
                if len(response_labels) >= 1:
                    true_ident = response_labels[0].get('ident', '')
                if len(response_labels) >= 2:
                    false_ident = response_labels[1].get('ident', '')
            
            resprocessing = item_el.find('resprocessing')
            
            if resprocessing is not None:
                for respcondition in resprocessing.findall('respcondition'):
                    conditionvar = respcondition.find('conditionvar')
                    if conditionvar is not None:
                        varequal = conditionvar.find('varequal')
                        if varequal is not None and varequal.get('respident') == question_lid:
                            answer_ident = varequal.text
                            
                            # Match answer_ident to determine if it's True or False
                            if true_ident and answer_ident == true_ident:
                                setvar = respcondition.find('setvar')
                                if setvar is not None:
                                    try:
                                        tf_data['true_weight'] = float(setvar.text)
                                    except (ValueError, TypeError):
                                        pass
                                
                                # Get feedback
                                displayfeedback = respcondition.find('displayfeedback')
                                if displayfeedback is not None:
                                    feedback_ident = displayfeedback.get('linkrefid', '')
                                    feedback_el = item_el.find(f".//itemfeedback[@ident='{feedback_ident}']")
                                    if feedback_el is not None:
                                        tf_data['true_feedback'] = self._extract_text_from_feedback(feedback_el)
                            
                            elif false_ident and answer_ident == false_ident:
                                setvar = respcondition.find('setvar')
                                if setvar is not None:
                                    try:
                                        tf_data['false_weight'] = float(setvar.text)
                                    except (ValueError, TypeError):
                                        pass
                                
                                # Get feedback
                                displayfeedback = respcondition.find('displayfeedback')
                                if displayfeedback is not None:
                                    feedback_ident = displayfeedback.get('linkrefid', '')
                                    feedback_el = item_el.find(f".//itemfeedback[@ident='{feedback_ident}']")
                                    if feedback_el is not None:
                                        tf_data['false_feedback'] = self._extract_text_from_feedback(feedback_el)
        
        return tf_data
    
    def _parse_fill_in_the_blanks(self, item_el, question_ident):
        """
        Parse fill in the blanks question data.
        Mirrors generate_fill_in_the_blanks() from XmlWriter.
        """
        fib_data = {
            'fibs': []  # List of fibquestion and fibanswer items in order
        }
        
        presentation = item_el.find('presentation')
        if presentation is None:
            return fib_data
        
        flow = presentation.find('flow')
        if flow is None:
            return fib_data
        
        # Parse flow elements in order (alternating fibquestion and fibanswer)
        idx = 1
        for child in flow:
            if child.tag == 'material':
                # This is a fibquestion (text part)
                mattext = child.find('mattext')
                text = ''
                if mattext is not None:
                    # Don't clean CDATA for FIB - preserve original spacing
                    text = mattext.text if mattext.text else ''
                
                fib_data['fibs'].append({
                    'type': 'fibquestion',
                    'text': text,
                    'order': idx
                })
            
            elif child.tag == 'response_str':
                # This is a fibanswer (blank)
                question_ans = question_ident + str(idx) + "_ANS"
                
                # Find answers from resprocessing
                answers = []
                resprocessing = item_el.find('resprocessing')
                if resprocessing is not None:
                    for respcondition in resprocessing.findall('respcondition'):
                        conditionvar = respcondition.find('conditionvar')
                        if conditionvar is not None:
                            varequal = conditionvar.find('varequal')
                            if varequal is not None and varequal.get('respident') == question_ans:
                                answer_text = varequal.text if varequal.text else ''
                                if answer_text:
                                    answers.append(answer_text)
                
                fib_data['fibs'].append({
                    'type': 'fibanswer',
                    'text': ','.join(answers) if answers else '',
                    'order': idx,
                    'size': 30  # Default from XmlWriter
                })
                idx += 1
        
        return fib_data
    
    def _parse_multi_select(self, item_el, question_ident):
        """
        Parse multi-select question data.
        Mirrors generate_multi_select() from XmlWriter.
        """
        ms_data = {
            'randomize': False,
            'enumeration': 4,
            'style': 2,
            'grading_type': 2,
            'answers': []
        }
        
        presentation = item_el.find('presentation')
        if presentation is None:
            return ms_data
        
        flow = presentation.find('flow')
        if flow is None:
            return ms_data
        
        # Parse response_extension
        response_ext = flow.find('response_extension')
        if response_ext is not None:
            enumeration_el = response_ext.find('{http://desire2learn.com/xsd/d2lcp_v2p0}enumeration')
            if enumeration_el is not None and enumeration_el.text:
                try:
                    ms_data['enumeration'] = int(enumeration_el.text)
                except (ValueError, TypeError):
                    pass
            
            grading_type_el = response_ext.find('{http://desire2learn.com/xsd/d2lcp_v2p0}grading_type')
            if grading_type_el is not None and grading_type_el.text:
                try:
                    ms_data['grading_type'] = int(grading_type_el.text)
                except (ValueError, TypeError):
                    pass
        
        # Parse response_lid
        response_lid = flow.find('response_lid')
        if response_lid is not None:
            question_lid = response_lid.get('ident', '')
            
            # Check shuffle
            render_choice = response_lid.find('render_choice')
            if render_choice is not None:
                ms_data['randomize'] = render_choice.get('shuffle', 'no').lower() == 'yes'
            
            # Parse answers
            answer_index = 1
            for flow_label in response_lid.findall('.//flow_label'):
                response_label = flow_label.find('response_label')
                if response_label is not None:
                    answer_ident = response_label.get('ident', '')
                    
                    # Extract answer text
                    mattext = response_label.find('.//mattext')
                    answer_text = ''
                    if mattext is not None:
                        raw_text = mattext.text if mattext.text else ''
                        # Clean CDATA whitespace while preserving HTML tags
                        answer_text = self._clean_cdata_text(raw_text)
                    
                    # Determine if correct from resprocessing
                    is_correct = False
                    answer_feedback = None
                    resprocessing = item_el.find('resprocessing')
                    if resprocessing is not None:
                        for respcondition in resprocessing.findall('respcondition'):
                            conditionvar = respcondition.find('conditionvar')
                            if conditionvar is not None:
                                varequal = conditionvar.find('varequal')
                                if varequal is not None and varequal.get('respident') == question_lid:
                                    if varequal.text == answer_ident:
                                        setvar = respcondition.find('setvar')
                                        if setvar is not None:
                                            # If setvar adds to D2L_Correct, it's a correct answer
                                            if setvar.get('varname') == 'D2L_Correct':
                                                is_correct = True
                                        
                                        # Find answer-specific feedback
                                        displayfeedback = respcondition.find('displayfeedback')
                                        if displayfeedback is not None:
                                            feedback_ident = displayfeedback.get('linkrefid', '')
                                            feedback_el = item_el.find(f".//itemfeedback[@ident='{feedback_ident}']")
                                            if feedback_el is not None:
                                                answer_feedback = self._extract_text_from_feedback(feedback_el)
                    
                    ms_data['answers'].append({
                        'answer': answer_text,
                        'is_correct': is_correct,
                        'answer_feedback': answer_feedback,
                        'order': answer_index
                    })
                    answer_index += 1
        
        return ms_data
    
    def _parse_matching(self, item_el, question_ident):
        """
        Parse matching question data.
        Mirrors generate_matching() from XmlWriter.
        """
        mat_data = {
            'grading_type': 0,
            'choices': []
        }
        
        presentation = item_el.find('presentation')
        if presentation is None:
            return mat_data
        
        flow = presentation.find('flow')
        if flow is None:
            return mat_data
        
        # Parse response_extension for grading_type
        response_ext = flow.find('response_extension')
        if response_ext is not None:
            grading_type_el = response_ext.find('{http://desire2learn.com/xsd/d2lcp_v2p0}grading_type')
            if grading_type_el is not None and grading_type_el.text:
                try:
                    mat_data['grading_type'] = int(grading_type_el.text)
                except (ValueError, TypeError):
                    pass
        
        # Collect all unique matching answers first (from all render_choices)
        matching_answers = {}
        
        # Find all response_grp elements (one per choice)
        response_grps = flow.findall('response_grp')
        
        # First pass: collect all possible answers from all choices
        for response_grp in response_grps:
            render_choice = response_grp.find('render_choice')
            if render_choice is not None:
                # Find all response_label elements directly (they may all be in one flow_label)
                for response_label in render_choice.findall('.//response_label'):
                    answer_ident = response_label.get('ident', '')
                    mattext = response_label.find('.//mattext')
                    if mattext is not None:
                        raw_text = mattext.text if mattext.text else ''
                        # Clean CDATA whitespace while preserving HTML tags
                        answer_text = self._clean_cdata_text(raw_text)
                        if answer_text and answer_ident not in matching_answers:
                            matching_answers[answer_ident] = answer_text
        
        # Second pass: process each choice and find its correct answer
        for response_grp in response_grps:
            choice_ident = response_grp.get('respident', '')
            
            # Get choice text from material
            material = response_grp.find('material')
            choice_text = ''
            if material is not None:
                mattext = material.find('mattext')
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ''
                    # Clean CDATA whitespace while preserving HTML tags
                    choice_text = self._clean_cdata_text(raw_text)
            
            # Find correct answer from resprocessing
            correct_answer_ident = None
            resprocessing = item_el.find('resprocessing')
            if resprocessing is not None:
                for respcondition in resprocessing.findall('respcondition'):
                    conditionvar = respcondition.find('conditionvar')
                    if conditionvar is not None:
                        varequal = conditionvar.find('varequal')
                        if varequal is not None and varequal.get('respident') == choice_ident:
                            setvar = respcondition.find('setvar')
                            if setvar is not None and setvar.get('varname') == 'D2L_Correct':
                                correct_answer_ident = varequal.text
                                break  # Found the correct answer for this choice
            
            # Build matching answers list for this choice
            matching_answers_list = []
            if correct_answer_ident and correct_answer_ident in matching_answers:
                matching_answers_list.append({
                    'answer_text': matching_answers[correct_answer_ident]
                })
            
            mat_data['choices'].append({
                'choice_text': choice_text,
                'matching_answers': matching_answers_list
            })
        
        return mat_data
    
    def _parse_ordering(self, item_el, question_ident):
        """
        Parse ordering question data.
        Mirrors generate_ordering() from XmlWriter.
        """
        ord_data = {
            'items': []
        }
        
        presentation = item_el.find('presentation')
        if presentation is None:
            return ord_data
        
        flow = presentation.find('flow')
        if flow is None:
            return ord_data
        
        # Find response_grp with rcardinality="Ordered"
        response_grp = flow.find('response_grp[@rcardinality="Ordered"]')
        if response_grp is None:
            return ord_data
        
        render_choice = response_grp.find('render_choice')
        if render_choice is None:
            return ord_data
        
        # Parse ordering items
        # Find all response_label elements directly (they may all be in one flow_label)
        order_index = 1
        for response_label in render_choice.findall('.//response_label'):
            ident_num = response_label.get('ident', '')
            
            # Extract text
            mattext = response_label.find('.//mattext')
            text = ''
            if mattext is not None:
                raw_text = mattext.text if mattext.text else ''
                # Clean CDATA whitespace while preserving HTML tags
                text = self._clean_cdata_text(raw_text)
            
            # Find feedback
            ord_feedback = None
            question_ident_feedback = question_ident + "_IF"
            feedback_ident = question_ident_feedback + str(order_index)
            feedback_el = item_el.find(f".//itemfeedback[@ident='{feedback_ident}']")
            if feedback_el is not None:
                ord_feedback = self._extract_text_from_feedback(feedback_el)
            
            ord_data['items'].append({
                'text': text,
                'order': order_index,
                'ord_feedback': ord_feedback
            })
            order_index += 1
        
        return ord_data
    
    def _parse_written_response(self, item_el, question_ident):
        """
        Parse written response question data.
        Mirrors generate_written_response() from XmlWriter.
        """
        wr_data = {
            'enable_student_editor': False,
            'initial_text': None,
            'answer_key': '',
            'enable_attachments': False
        }
        
        # Parse response_extension
        presentation = item_el.find('presentation')
        if presentation is not None:
            flow = presentation.find('flow')
            if flow is not None:
                response_ext = flow.find('response_extension')
                if response_ext is not None:
                    editor_el = response_ext.find('{http://desire2learn.com/xsd/d2lcp_v2p0}has_htmleditor')
                    if editor_el is not None:
                        editor_text = editor_el.text if editor_el.text else ''
                        wr_data['enable_student_editor'] = editor_text.lower() == 'yes'
        
        # Parse answer_key
        answer_key_el = item_el.find('answer_key')
        if answer_key_el is not None:
            answer_key_mat = answer_key_el.find('answer_key_material')
            if answer_key_mat is not None:
                mattext = answer_key_mat.find('.//mattext')
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ''
                    # Clean CDATA whitespace while preserving HTML tags
                    wr_data['answer_key'] = self._clean_cdata_text(raw_text)
        
        # Parse initial_text (if present)
        initial_text_el = item_el.find('initial_text')
        if initial_text_el is not None:
            initial_text_mat = initial_text_el.find('initial_text_material')
            if initial_text_mat is not None:
                mattext = initial_text_mat.find('.//mattext')
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ''
                    # Clean CDATA whitespace while preserving HTML tags
                    cleaned_text = self._clean_cdata_text(raw_text)
                    wr_data['initial_text'] = cleaned_text if cleaned_text else None
        
        return wr_data
    
    def populate_django_models(self, question_library=None):
        """
        Populate Django models from parsed SCORM XML data.
        
        Args:
            question_library: Optional existing QuestionLibrary instance to use.
                            If None, a new one will be created.
        
        Returns:
            QuestionLibrary: The QuestionLibrary instance with all sections and questions
        """
        # Parse questiondb to get structure
        question_library_data = self.parse_questiondb()
        
        # Get main title from first section (base section)
        main_title = ''
        if question_library_data['sections']:
            main_title = question_library_data['sections'][0].get('title', '')
        
        # Use existing QuestionLibrary or create a new one
        if question_library is None:
            question_library = QuestionLibrary.objects.create(
                main_title=main_title,
                shuffle=False  # Will be set from section data
            )
        else:
            # Update existing instance with parsed data
            question_library.main_title = main_title
            question_library.save()
        
        # Process sections
        section_order = 1
        question_index = 1  # Global question index that continues across all sections
        for section_data in question_library_data['sections']:
            has_nested_sections = len(section_data.get('sections', [])) > 0
            has_direct_questions = len(section_data.get('questions', [])) > 0
            has_text = section_data.get('text', '').strip() != ''
            
            # If root section has questions or text, create it as the first section (is_main_content=True)
            # This section represents the main_title and should be in the sections array
            if has_direct_questions or has_text:
                # Create the root section as the first section with is_main_content=True
                section = Section.objects.create(
                    question_library=question_library,
                    is_main_content=True,
                    order=section_order,
                    title=section_data.get('title', ''),
                    is_title_displayed=section_data.get('is_title_displayed', True),
                    text=section_data.get('text', ''),
                    is_text_displayed=section_data.get('is_text_displayed', False),
                    shuffle=section_data.get('shuffle', False)
                )
                
                # Process questions in this section (continue question_index)
                for question_data in section_data.get('questions', []):
                    question = self._create_question_model(section, question_data, question_index)
                    question_index += 1
                
                # Process nested sections (if any)
                for nested_section_data in section_data.get('sections', []):
                    nested_section = Section.objects.create(
                        question_library=question_library,
                        is_main_content=False,
                        order=section_order + 1,
                        title=nested_section_data.get('title', ''),
                        is_title_displayed=nested_section_data.get('is_title_displayed', True),
                        text=nested_section_data.get('text', ''),
                        is_text_displayed=nested_section_data.get('is_text_displayed', False),
                        shuffle=nested_section_data.get('shuffle', False)
                    )
                    
                    # Process questions in nested section (continue question_index)
                    for question_data in nested_section_data.get('questions', []):
                        question = self._create_question_model(nested_section, question_data, question_index)
                        question_index += 1
                    
                    section_order += 1
                
                section_order += 1
            elif has_nested_sections:
                # Root section has nested sections but no questions/text - don't create Section for it
                # Only process nested sections
                for nested_section_data in section_data.get('sections', []):
                    nested_section = Section.objects.create(
                        question_library=question_library,
                        is_main_content=False,
                        order=section_order,
                        title=nested_section_data.get('title', ''),
                        is_title_displayed=nested_section_data.get('is_title_displayed', True),
                        text=nested_section_data.get('text', ''),
                        is_text_displayed=nested_section_data.get('is_text_displayed', False),
                        shuffle=nested_section_data.get('shuffle', False)
                    )
                    
                    # Process questions in nested section (continue question_index)
                    for question_data in nested_section_data.get('questions', []):
                        question = self._create_question_model(nested_section, question_data, question_index)
                        question_index += 1
                    
                    section_order += 1
        
        return question_library
    
    def _create_question_model(self, section, question_data, index):
        """Create a Question model and related question type models from parsed data."""
        question = Question.objects.create(
            section=section,
            index=index,
            title=question_data.get('title', ''),
            questiontype=question_data.get('question_type_code', ''),
            text=question_data.get('text', ''),
            points=question_data.get('points', 1.0),
            hint=question_data.get('hint'),
            feedback=question_data.get('feedback')
        )
        
        question_type_code = question_data.get('question_type_code', '')
        specific_data = question_data.get('question_specific_data', {})
        
        if question_type_code == 'MC':
            self._create_multiple_choice_model(question, specific_data)
        elif question_type_code == 'TF':
            self._create_true_false_model(question, specific_data)
        elif question_type_code == 'FIB':
            self._create_fib_model(question, specific_data)
        elif question_type_code == 'MS':
            self._create_multiple_select_model(question, specific_data)
        elif question_type_code == 'MAT':
            self._create_matching_model(question, specific_data)
        elif question_type_code == 'ORD':
            self._create_ordering_model(question, specific_data)
        elif question_type_code == 'WR':
            self._create_written_response_model(question, specific_data)
        
        return question
    
    def _create_multiple_choice_model(self, question, mc_data):
        """Create MultipleChoice and MultipleChoiceAnswer models."""
        mc = MultipleChoice.objects.create(
            question=question,
            randomize=mc_data.get('randomize', False),
            enumeration=mc_data.get('enumeration', 4)
        )
        
        for answer_data in mc_data.get('answers', []):
            MultipleChoiceAnswer.objects.create(
                multiple_choice=mc,
                order=answer_data.get('order', 1),
                answer=answer_data.get('answer', ''),
                answer_feedback=answer_data.get('answer_feedback'),
                weight=answer_data.get('weight', 0.0)
            )
    
    def _create_true_false_model(self, question, tf_data):
        """Create TrueFalse model."""
        TrueFalse.objects.create(
            question=question,
            true_weight=tf_data.get('true_weight', 0.0),
            true_feedback=tf_data.get('true_feedback'),
            false_weight=tf_data.get('false_weight', 0.0),
            false_feedback=tf_data.get('false_feedback'),
            enumeration=tf_data.get('enumeration', 4)
        )
    
    def _create_fib_model(self, question, fib_data):
        """Create Fib models for fill in the blanks."""
        for fib_item in fib_data.get('fibs', []):
            Fib.objects.create(
                question=question,
                type=fib_item.get('type', 'fibquestion'),
                text=fib_item.get('text', ''),
                order=fib_item.get('order', 1),
                size=fib_item.get('size')
            )
    
    def _create_multiple_select_model(self, question, ms_data):
        """Create MultipleSelect and MultipleSelectAnswer models."""
        ms = MultipleSelect.objects.create(
            question=question,
            randomize=ms_data.get('randomize', False),
            enumeration=ms_data.get('enumeration', 4),
            style=ms_data.get('style', 2),
            grading_type=ms_data.get('grading_type', 2)
        )
        
        for answer_data in ms_data.get('answers', []):
            MultipleSelectAnswer.objects.create(
                multiple_select=ms,
                order=answer_data.get('order', 1),
                answer=answer_data.get('answer', ''),
                answer_feedback=answer_data.get('answer_feedback'),
                is_correct=answer_data.get('is_correct', False)
            )
    
    def _create_matching_model(self, question, mat_data):
        """Create Matching, MatchingChoice, and MatchingAnswer models."""
        matching = Matching.objects.create(
            question=question,
            grading_type=mat_data.get('grading_type', 0)
        )
        
        for choice_data in mat_data.get('choices', []):
            matching_choice = MatchingChoice.objects.create(
                matching=matching,
                choice_text=choice_data.get('choice_text', '')
            )
            
            for answer_data in choice_data.get('matching_answers', []):
                MatchingAnswer.objects.create(
                    matching_choice=matching_choice,
                    answer_text=answer_data.get('answer_text', '')
                )
    
    def _create_ordering_model(self, question, ord_data):
        """Create Ordering models."""
        for item_data in ord_data.get('items', []):
            Ordering.objects.create(
                question=question,
                text=item_data.get('text', ''),
                order=item_data.get('order', 1),
                ord_feedback=item_data.get('ord_feedback')
            )
    
    def _create_written_response_model(self, question, wr_data):
        """Create WrittenResponse model."""
        WrittenResponse.objects.create(
            question=question,
            enable_student_editor=wr_data.get('enable_student_editor', False),
            initial_text=wr_data.get('initial_text'),
            answer_key=wr_data.get('answer_key', ''),
            enable_attachments=wr_data.get('enable_attachments', False)
        )
    
    def format_to_markdown(self, question_library):
        """
        Format parsed questions from Django models into markdown/text format
        that matches the formatter_output structure (body text with questions).
        This reconstructs the markdown that would have come from the original DOCX.
        This can then be converted to DOCX using pandoc.
        
        Args:
            question_library: QuestionLibrary Django model instance
            
        Returns:
            str: Markdown formatted text (formatter_output format) ready for DOCX conversion
        """
        lines = []
        
        # Add main title as H1 heading if it exists
        if question_library.main_title:
            # Clean HTML from main title
            main_title = question_library.main_title
            try:
                soup = BeautifulSoup(main_title, 'html.parser')
                main_title = soup.get_text(separator=' ', strip=True)
            except:
                main_title = re.sub(r'\s+', ' ', main_title).strip()
            lines.append(f"# {main_title}")
            lines.append("")  # Add blank line after title
        
        # Process sections
        sections = question_library.get_sections()
        for section in sections:
            # Skip root section (is_main_content=True) - don't wrap it with #section markers
            # Only wrap non-root sections with #section and /section markers
            if not section.is_main_content:
                lines.append("#section")
            
            # Add section title if present and should be displayed (## for markdown heading)
            if section.title and section.is_title_displayed:
                # Clean HTML from section title for display
                section_title_display = section.title
                try:
                    soup = BeautifulSoup(section_title_display, 'html.parser')
                    section_title_display = soup.get_text(separator=' ', strip=True)
                except:
                    section_title_display = re.sub(r'\s+', ' ', section_title_display).strip()
                lines.append(f"## {section_title_display}")
            
            # Add section text if present and should be displayed
            if section.text and section.is_text_displayed:
                # Convert HTML back to markdown if needed
                section_text = section.text
                lines.append(section_text)
            
            # Process questions in this section
            questions = section.get_questions()
            for question in questions:
                question_markdown = self._format_question_to_markdown(question)
                lines.append(question_markdown)
                lines.append("")  # Add blank line between questions
            
            # Close section marker for non-root sections
            if not section.is_main_content:
                lines.append("/section")
                lines.append("")  # Add blank line after section
        
        # Join with newlines and ensure proper formatting
        result = "\n".join(lines)
        if result and not result.endswith("\n"):
            result += "\n"
        return result
    
    def _format_question_to_markdown(self, question):
        """
        Format a single question to markdown format matching the raw_content format
        that the ANTLR questionparser expects.
        Format: [number.] Type: ... Title: ... Points: ... [question text] [answers] [@Hint:] [@Feedback:]
        """
        lines = []
        
        # Question header: Type, Title, Points (each on separate line)
        # Each header on its own line
        if question.questiontype:
            lines.append(f"Type: {question.questiontype}")
        if question.title:
            lines.append(f"Title: {question.title}")
        if question.points:
            # Normalize points: remove trailing zeros and decimal if not needed (e.g., 1.0000 -> 1, 1.5 -> 1.5)
            normalized_points = str(float(question.points)).rstrip('0').rstrip('.')
            lines.append(f"Points: {normalized_points}")
        
        # Add question text (HTML format from SCORM, convert to plain text)
        # Prefix with question number if available (e.g., "1. Question text")
        # Note: For FIB questions, skip displaying question.text here since FIB formatting includes all text parts
        if question.text and question.questiontype != 'FIB':
            # Convert HTML to plain text if needed
            question_text = question.text
            # Remove HTML tags but keep content
            import re
            from bs4 import BeautifulSoup
            try:
                # Try to parse as HTML and extract text
                soup = BeautifulSoup(question_text, 'html.parser')
                question_text = soup.get_text(separator=' ', strip=True)
            except:
                # If not HTML, use as is but clean up extra whitespace
                question_text = re.sub(r'\s+', ' ', question_text).strip()
            
            # Prefix with question number if available
            question_number = None
            if question.index is not None:
                question_number = question.index
            elif question.number_provided is not None:
                question_number = question.number_provided
            
            if question_number is not None:
                lines.append(f"{question_number}. {question_text}")
            else:
                lines.append(question_text)
        
        # Format question-specific content based on type
        question_type = question.questiontype
        if question_type == 'MC':
            answer_text = self._format_multiple_choice_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == 'TF':
            answer_text = self._format_true_false_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == 'FIB':
            answer_text = self._format_fib_markdown(question)
            if answer_text:
                # For FIB questions, prefix with question number since we skipped question.text above
                question_number = None
                if question.index is not None:
                    question_number = question.index
                elif question.number_provided is not None:
                    question_number = question.number_provided
                
                if question_number is not None:
                    lines.append(f"{question_number}. {answer_text}")
                else:
                    lines.append(answer_text)
        elif question_type == 'MS':
            answer_text = self._format_multi_select_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == 'MAT':
            answer_text = self._format_matching_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == 'ORD':
            answer_text = self._format_ordering_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == 'WR':
            answer_text = self._format_written_response_markdown(question)
            if answer_text:
                lines.append(answer_text)
        
        # Add hint if present (format: @Hint: or @HINT:)
        if question.hint:
            hint_text = question.hint
            try:
                soup = BeautifulSoup(hint_text, 'html.parser')
                hint_text = soup.get_text(separator=' ', strip=True)
            except:
                hint_text = re.sub(r'\s+', ' ', hint_text).strip()
            lines.append(f"@Hint: {hint_text}")
        
        # Add feedback if present (format: @Feedback: or @FEEDBACK:)
        if question.feedback:
            feedback_text = question.feedback
            try:
                soup = BeautifulSoup(feedback_text, 'html.parser')
                feedback_text = soup.get_text(separator=' ', strip=True)
            except:
                feedback_text = re.sub(r'\s+', ' ', feedback_text).strip()
            lines.append(f"@Feedback: {feedback_text}")
        
        # Use double newlines so each logical line becomes a paragraph (hard breaks, not soft)
        return "\n\n".join(lines)
    
    def _format_multiple_choice_markdown(self, question):
        """
        Format multiple choice question answers.
        Format: a. [answer text] or *a. [answer text] for correct answers
        """
        lines = []
        mc = question.get_multiple_choice()
        if mc:
            answers = mc.get_multiple_choice_answers()
            for idx, answer in enumerate(answers, start=1):
                letter = chr(96 + idx)  # a, b, c, etc.
                # Correct answer has * before the letter (weight > 0)
                marker = "*" if answer.weight and answer.weight > 0 else ""
                # Clean HTML from answer text
                answer_text = answer.answer
                try:
                    soup = BeautifulSoup(answer_text, 'html.parser')
                    answer_text = soup.get_text(separator=' ', strip=True)
                except:
                    answer_text = re.sub(r'\s+', ' ', answer_text).strip()
                # Indent as level 2 list (4 spaces for markdown level 2)
                lines.append(f"    {letter}. {marker}{answer_text}")
                if answer.answer_feedback:
                    feedback_text = answer.answer_feedback
                    try:
                        soup = BeautifulSoup(feedback_text, 'html.parser')
                        feedback_text = soup.get_text(separator=' ', strip=True)
                    except:
                        feedback_text = re.sub(r'\s+', ' ', feedback_text).strip()
                    lines.append(f"    @Feedback: {feedback_text}")
        return "\n".join(lines)
    
    def _format_true_false_markdown(self, question):
        """
        Format true/false question answers.
        Format: a. True / b. False with * after letter for correct answer (e.g., a. *True)
        """
        lines = []
        tf = question.get_true_false()
        if tf:
            true_marker = "*" if tf.true_weight and tf.true_weight > 0 else ""
            false_marker = "*" if tf.false_weight and tf.false_weight > 0 else ""
            # Indent as level 2 list (4 spaces for markdown level 2)
            lines.append(f"    a. {true_marker}True")
            if tf.true_feedback:
                lines.append(f"    @Feedback: {tf.true_feedback}")
            lines.append(f"    b. {false_marker}False")
            if tf.false_feedback:
                lines.append(f"    @Feedback: {tf.false_feedback}")
        return "\n".join(lines)
    
    def _format_fib_markdown(self, question):
        """
        Format fill in the blanks question.
        Format: Question text with [answer] markers where answers go
        Example: "A [rose,flower] by any other name would smell as [sweet,good]."
        Note: Clean HTML tags but preserve spacing (CDATA cleaning was skipped during parsing).
        """
        lines = []
        fibs = question.get_fibs()
        current_text = ""
        for fib in fibs:
            if fib.type == 'fibquestion':
                if fib.text:
                    # Clean HTML tags but preserve spacing
                    from bs4 import BeautifulSoup
                    try:
                        soup = BeautifulSoup(fib.text, 'html.parser')
                        cleaned_text = soup.get_text(separator=' ', strip=False)
                        current_text += cleaned_text
                    except Exception:
                        # Fallback: use text as-is if BeautifulSoup fails
                        current_text += fib.text
            elif fib.type == 'fibanswer':
                # Insert answer in brackets [answer] where the blank should be
                if fib.text:
                    current_text += f" [{fib.text}]"
                else:
                    current_text += " [ ]"
        if current_text:
            lines.append(current_text)
        return "\n".join(lines)
    
    def _format_multi_select_markdown(self, question):
        """
        Format multi-select question answers.
        Format: a. [answer] or *a. [answer] for correct answers
        """
        lines = []
        ms = question.get_multiple_select()
        if ms:
            answers = ms.get_multiple_select_answers()
            for idx, answer in enumerate(answers, start=1):
                letter = chr(96 + idx)  # a, b, c, etc.
                marker = "*" if answer.is_correct else ""
                # Clean HTML from answer text
                answer_text = answer.answer
                try:
                    soup = BeautifulSoup(answer_text, 'html.parser')
                    answer_text = soup.get_text(separator=' ', strip=True)
                except:
                    answer_text = re.sub(r'\s+', ' ', answer_text).strip()
                # Indent as level 2 list (4 spaces for markdown level 2)
                lines.append(f"    {letter}. {marker}{answer_text}")
                if answer.answer_feedback:
                    feedback_text = answer.answer_feedback
                    try:
                        soup = BeautifulSoup(feedback_text, 'html.parser')
                        feedback_text = soup.get_text(separator=' ', strip=True)
                    except:
                        feedback_text = re.sub(r'\s+', ' ', feedback_text).strip()
                    lines.append(f"    @Feedback: {feedback_text}")
        return "\n".join(lines)
    
    def _format_matching_markdown(self, question):
        """
        Format matching question.
        Format: a. choice_text = answer_text (on same line, with enumeration)
        Preserves inline HTML styling (bold, italic, etc.) but removes block-level tags (p, div, etc.)
        """
        lines = []
        matching = question.get_matching()
        if matching:
            choices = matching.get_matching_choices()
            for idx, choice in enumerate(choices, start=1):
                letter = chr(96 + idx)  # a, b, c, etc.
                
                # Remove block-level HTML tags but preserve inline styling
                choice_text = self._remove_block_tags_preserve_inline(choice.choice_text)
                
                # Use the related manager matching_answers (from ForeignKey in MatchingAnswer)
                answers = choice.matching_answers.all()
                if answers:
                    # Get the first matching answer (typically there's one per choice)
                    answer = answers[0]
                    answer_text = self._remove_block_tags_preserve_inline(answer.answer_text)
                    # Indent as level 2 list (4 spaces for markdown level 2)
                    lines.append(f"    {letter}. {choice_text} = {answer_text}")
                else:
                    # No answer found, just show choice
                    lines.append(f"    {letter}. {choice_text} =")
        return "\n".join(lines)
    
    def _remove_block_tags_preserve_inline(self, html_text):
        """
        Remove block-level HTML tags (p, div, etc.) but preserve inline styling tags (strong, em, b, i, etc.).
        This allows formatting like bold/italic to be preserved while removing tags that cause line breaks.
        Returns HTML string with inline tags preserved.
        """
        if not html_text:
            return ''
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Unwrap block-level tags (these cause line breaks) but preserve their content and inline tags
            block_tags = ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'ul', 'ol']
            for tag_name in block_tags:
                for tag in soup.find_all(tag_name):
                    # Unwrap removes the tag but keeps its content (including inline tags)
                    tag.unwrap()
            
            # Get the HTML string with inline tags preserved
            result = str(soup)
            # Clean up: remove leading/trailing whitespace and normalize internal whitespace
            # But preserve HTML tag structure
            result = re.sub(r'>\s+<', '><', result)  # Remove whitespace between tags
            result = re.sub(r'\s+', ' ', result)  # Normalize whitespace
            result = result.strip()
            return result
        except Exception:
            # Fallback: if parsing fails, just clean whitespace but preserve HTML structure
            cleaned = re.sub(r'>\s+<', '><', html_text)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return cleaned
    
    def _format_ordering_markdown(self, question):
        """
        Format ordering question.
        Format: lettered list (a., b., c., etc.) with HTML tags cleaned, indented as level 2 list
        """
        lines = []
        orderings = question.get_orderings()
        for idx, ordering in enumerate(orderings, start=1):
            letter = chr(96 + idx)  # a, b, c, etc.
            # Clean HTML from ordering text
            ordering_text = ordering.text
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(ordering_text, 'html.parser')
                ordering_text = soup.get_text(separator=' ', strip=True)
            except:
                import re
                ordering_text = re.sub(r'\s+', ' ', ordering_text).strip()
            # Indent as level 2 list (4 spaces for markdown level 2)
            lines.append(f"    {letter}. {ordering_text}")
            if ordering.ord_feedback:
                feedback_text = ordering.ord_feedback
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(feedback_text, 'html.parser')
                    feedback_text = soup.get_text(separator=' ', strip=True)
                except:
                    import re
                    feedback_text = re.sub(r'\s+', ' ', feedback_text).strip()
                lines.append(f"    @Feedback: {feedback_text}")
        return "\n".join(lines)
    
    def _format_written_response_markdown(self, question):
        """
        Format written response question.
        Format: Blank line, then "Correct Answer:" indented, then indented answer text.
        Use double newlines to ensure hard paragraph breaks (not soft returns) in DOCX.
        """
        lines = []
        wr = question.get_written_response()
        if wr and wr.answer_key:
            # Add blank line first (double newline for hard paragraph break)
            lines.append("")
            # Clean HTML from answer text
            answer_text = wr.answer_key
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(answer_text, 'html.parser')
                answer_text = soup.get_text(separator=' ', strip=True)
            except:
                import re
                answer_text = re.sub(r'\s+', ' ', answer_text).strip()
            # Indent with regular spaces (3 for label, 7 for answer) to mimic margin
            # Avoid 4+ leading spaces to prevent markdown list or code block detection
            lines.append(f"Correct Answer:")
            lines.append(f"{answer_text}")
        # Use double newlines so each logical line becomes a paragraph (hard breaks)
        return "\n\n".join(lines)
    
    def convert_markdown_to_docx(self, markdown_text, output_path):
        """
        Convert markdown text to DOCX file using pandoc (reverse of run_pandoc_task).
        This is the final step to generate DOCX from the formatted markdown.
        
        Args:
            markdown_text: Markdown formatted text (from format_to_markdown)
            output_path: Path where the DOCX file should be saved
            
        Returns:
            str: Path to the created DOCX file
        """
        import pypandoc
        import tempfile
        import os
        
        # Create a temporary markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_md:
            temp_md.write(markdown_text)
            temp_md_path = temp_md.name
        
        try:
            # Convert markdown to DOCX using pandoc (reverse of DOCX → markdown)
            # Use similar settings as the forward conversion but in reverse
            pypandoc.convert_file(
                temp_md_path,
                format='markdown_github+fancy_lists+emoji+hard_line_breaks+all_symbols_escapable+escaped_line_breaks+pipe_tables+startnum+tex_math_dollars',
                to='docx+empty_paragraphs',
                outputfile=output_path,
                extra_args=[
                    '--no-highlight',
                    '--preserve-tabs',
                    '--wrap=preserve',
                    '--indent=false',
                    '--mathml',
                    '--ascii'
                ]
            )
        finally:
            # Clean up temporary markdown file
            if os.path.exists(temp_md_path):
                os.unlink(temp_md_path)
        
        return output_path
