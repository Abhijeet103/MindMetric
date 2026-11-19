import csv
import io
import json
from datetime import timedelta
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr
from zipfile import ZipFile, ZIP_DEFLATED

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from backend.apps.assessments.config import ASSESSMENT_CONFIG
from backend.apps.pages.models import RecruiterAssessment, RecruiterQuestionImport
from backend.apps.pages.question_import import ImportProblem, default_mapping, read_upload, resolve_answer, validate_questions
from backend.apps.tenants.models import Tenant

HEADERS = ['Question', 'Option A', 'Option B', 'Option C', 'Option D', 'Correct answer', 'Subject', 'Explanation']
ROWS = [HEADERS, ['What is 20% of 150?', '20', '25', '30', '35', 'C', 'Arithmetic', '150 × 0.20 = 30.'], ['All invoices need approval. An invoice can skip approval.', 'True', 'False', '', '', 'B', 'Policy', 'The claim contradicts the rule.']]


def csv_upload(rows=ROWS, name='questions.csv'):
    output = io.StringIO()
    csv.writer(output).writerows(rows)
    return SimpleUploadedFile(name, output.getvalue().encode('utf-8'), content_type='text/csv')


def xlsx_upload(sheets=None, dimension=None):
    """Minimal OOXML fixture, built without a spreadsheet-authoring dependency."""
    sheets = sheets or [('Questions', ROWS)]
    output = io.BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets)+1)) + '</Types>')
        archive.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + ''.join(f'<sheet name={quoteattr(name)} sheetId="{i}" r:id="rId{i}"/>' for i, (name, _) in enumerate(sheets, 1)) + '</sheets></workbook>')
        archive.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sheets)+1)) + '</Relationships>')
        for sheet_index, (_, rows) in enumerate(sheets, 1):
            xml_rows = []
            for row_index, row in enumerate(rows, 1):
                cells = []
                for col, value in enumerate(row):
                    letters, number = '', col+1
                    while number:
                        number, rem = divmod(number-1, 26)
                        letters = chr(65+rem)+letters
                    ref = letters+str(row_index)
                    if isinstance(value, tuple):
                        kind, content = value
                        if kind == 'formula':
                            cells.append(f'<c r="{ref}"><f>{escape(content)}</f><v>0</v></c>')
                        else:
                            cells.append(f'<c r="{ref}" t="e"><v>{escape(content)}</v></c>')
                    elif isinstance(value, (int, float)):
                        cells.append(f'<c r="{ref}"><v>{value}</v></c>')
                    else:
                        cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
                xml_rows.append(f'<row r="{row_index}">' + ''.join(cells) + '</row>')
            archive.writestr(f'xl/worksheets/sheet{sheet_index}.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' + (f'<dimension ref="{dimension}"/>' if dimension else '') + '<sheetData>' + ''.join(xml_rows) + '</sheetData></worksheet>')
    return SimpleUploadedFile('questions.xlsx', output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


class QuestionImportParserTests(SimpleTestCase):
    def test_xlsx_csv_and_numeric_values_parse_to_same_questions(self):
        for upload in (csv_upload(), xlsx_upload()):
            sheet = read_upload(upload)[0]
            questions, errors = validate_questions(sheet, 1, default_mapping(sheet, 1))
            self.assertFalse(errors)
            self.assertEqual([q['correct_answer']['answer'] for q in questions], ['30', 'False'])
        numeric = [HEADERS, ['Choose thirty', 20, 25.0, 30.0, 35, 'C', 'Arithmetic', '']]
        sheet = read_upload(xlsx_upload([('Numbers', numeric)]))[0]
        self.assertEqual(sheet['rows'][1][3], '30')

    def test_legacy_excel_fixture_preserves_numeric_options_and_keys(self):
        content = (Path(__file__).parent / 'fixtures' / 'recruiter-questions.xls').read_bytes()
        sheet = read_upload(SimpleUploadedFile('legacy.xls', content))[0]
        questions, errors = validate_questions(sheet, 1, default_mapping(sheet, 1))
        self.assertFalse(errors)
        self.assertEqual(questions[0]['correct_answer']['answer'], '4')
        self.assertEqual(questions[1]['correct_answer']['answer'], 'Not compliant')

    def test_oversized_zip_and_xml_entities_are_rejected(self):
        content = io.BytesIO()
        with ZipFile(content, 'w', ZIP_DEFLATED) as archive:
            archive.writestr('large.xml', b'x' * (21*1024*1024))
        with self.assertRaises(ImportProblem):
            read_upload(SimpleUploadedFile('oversized.xlsx', content.getvalue()))
        original = xlsx_upload().read()
        hostile = io.BytesIO()
        with ZipFile(io.BytesIO(original)) as source, ZipFile(hostile, 'w', ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == 'xl/worksheets/sheet1.xml':
                    data = b'<!DOCTYPE worksheet [<!ENTITY attack SYSTEM "file:///definitely-not-a-real-file">]>' + data.replace(b'What is 20% of 150?', b'&attack;')
                target.writestr(item.filename, data)
        with self.assertRaises(ImportProblem):
            read_upload(SimpleUploadedFile('entities.xlsx', hostile.getvalue()))

    def test_ambiguous_numeric_keys_require_explicit_format(self):
        options = [('A', '2'), ('B', '8'), ('C', '5')]
        self.assertIsNone(resolve_answer('2', options, 'auto'))
        self.assertEqual(resolve_answer('2', options, 'number'), '8')
        self.assertEqual(resolve_answer('2', options, 'text'), '2')
        self.assertEqual(resolve_answer('Option B', options, 'letter'), '8')
        self.assertIsNone(resolve_answer('D', options, 'letter'))

    def test_formula_and_error_cells_block_import_without_execution(self):
        for marker in [('formula', 'HYPERLINK("https://example.com", "click")'), ('error', '#DIV/0!')]:
            rows = [HEADERS, ['Question', 'One', marker, '', '', 'A', '', '']]
            sheet = read_upload(xlsx_upload([('Questions', rows)]))[0]
            questions, errors = validate_questions(sheet, 1, default_mapping(sheet, 1))
            self.assertFalse(questions)
            self.assertIn('formula or Excel error', errors[0]['messages'][0])

    def test_blank_duplicate_missing_and_invalid_rows_are_not_silently_skipped(self):
        rows = [HEADERS, ROWS[1], ['']*8, ROWS[1], ['Missing key', 'A1', 'B1', '', '', '', '', ''], ['Repeated options', 'Same', ' same ', '', '', 'A', '', '']]
        sheet = read_upload(csv_upload(rows))[0]
        questions, errors = validate_questions(sheet, 1, default_mapping(sheet, 1))
        self.assertEqual(len(questions), 1)
        self.assertEqual([error['row'] for error in errors], [4, 5, 6])
        self.assertIn('duplicate', errors[0]['messages'][0])

    def test_question_count_and_workbook_limits(self):
        rows = [HEADERS, *[[f'Question {i}', 'Yes', 'No', '', '', 'A', '', ''] for i in range(61)]]
        sheet = read_upload(csv_upload(rows))[0]
        _, errors = validate_questions(sheet, 1, default_mapping(sheet, 1))
        self.assertIn('60 questions', errors[-1]['messages'][0])
        for upload in [SimpleUploadedFile('bad.xlsx', b'not a zip'), SimpleUploadedFile('bad.xls', b'not xls'), SimpleUploadedFile('bad.pdf', b'pdf'), SimpleUploadedFile('large.csv', b'x'*(2*1024*1024+1)), xlsx_upload([('Huge', [['x']*41])]), csv_upload([['x']]*1001)]:
            with self.subTest(name=upload.name), self.assertRaises(ImportProblem):
                read_upload(upload)

    def test_inflated_dimensions_do_not_create_blank_millions_of_rows(self):
        sheet = read_upload(xlsx_upload(dimension='A1:XFD1048576'))[0]
        self.assertEqual(len(sheet['rows']), 3)

    def test_actual_data_after_row_limit_is_rejected(self):
        with self.assertRaises(ImportProblem):
            read_upload(xlsx_upload([('Too many', [['']]*1001 + [['late question']])]))

    def test_macro_extension_is_read_as_data_and_unsupported_files_rejected(self):
        upload = xlsx_upload()
        upload.name = 'questions.xlsm'
        self.assertEqual(read_upload(upload)[0]['rows'][0], HEADERS)
        with self.assertRaises(ImportProblem):
            read_upload(SimpleUploadedFile('questions.xlsb', b'invalid'))


class RecruiterExcelFlowTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Excel tests', slug='excel-tests', primary_domain='excel.example.com', tenant_type='platform', allowed_assessments=list(ASSESSMENT_CONFIG))
        self.host = {'HTTP_HOST': self.tenant.primary_domain}
        User = get_user_model()
        self.owner = User.objects.create_user(email='excel-owner@example.com', password='password123', account_type='recruiter', organization='Example company', tenant=self.tenant)
        self.other = User.objects.create_user(email='excel-other@example.com', password='password123', account_type='recruiter', tenant=self.tenant)
        self.student = User.objects.create_user(email='excel-student@example.com', password='password123', tenant=self.tenant)
        self.client.force_login(self.owner)
        self.upload_url = reverse('pages:recruiter-upload')
        self.settings = {'title':'Custom analyst test', 'organization':'Example company', 'role_title':'Analyst', 'duration_minutes':10, 'open_days':7, 'max_candidates':20, 'allowed_emails':'', 'instructions':'Use only the question information.'}

    def upload(self, file=None):
        response = self.client.post(self.upload_url, {'workbook': file or xlsx_upload()}, **self.host)
        self.assertEqual(response.status_code, 302)
        return RecruiterQuestionImport.objects.latest('created_at')

    def map(self, draft, mapping=None):
        mapping = mapping or {**default_mapping(draft.sheets[0], 1), 'sheet':0, 'header_row':1}
        response = self.client.post(reverse('pages:recruiter-import-map', args=[draft.pk]), mapping, **self.host)
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        return response

    def publish(self, draft):
        return self.client.post(reverse('pages:recruiter-import-preview', args=[draft.pk]), self.settings, **self.host)

    def test_full_upload_map_preview_publish_take_and_score(self):
        draft = self.upload()
        self.assertFalse(RecruiterAssessment.objects.exists())
        self.assertEqual(self.client.get(reverse('pages:recruiter-import-map', args=[draft.pk]), **self.host).status_code, 200)
        self.map(draft)
        self.assertFalse(draft.errors)
        preview_url = reverse('pages:recruiter-import-preview', args=[draft.pk])
        preview = self.client.get(preview_url, **self.host)
        self.assertContains(preview, 'Correct answer:')
        self.assertIn('no-store', preview.headers['Cache-Control'])
        self.assertEqual(self.publish(draft).status_code, 302)
        assessment = RecruiterAssessment.objects.get()
        self.assertEqual(len(assessment.custom_questions), 2)
        self.assertEqual(assessment.modules, [])
        self.assertContains(self.client.get(reverse('pages:recruiter-assessment', args=[assessment.pk]), **self.host), '2 questions')
        self.assertEqual(self.publish(draft).status_code, 302)
        self.assertEqual(RecruiterAssessment.objects.count(), 1)
        self.assertEqual(self.client.get(reverse('pages:recruiter-import-map', args=[draft.pk]), **self.host).status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.sheets, [])
        self.client.force_login(self.student)
        start = self.client.post(reverse('pages:recruiter-candidate-start', args=[assessment.share_token]), '{"consent":true}', content_type='application/json', **self.host)
        self.assertEqual(start.status_code, 201)
        self.assertEqual(start.json()['questions'][0]['question_text'], ROWS[1][0])
        self.assertNotIn('correct_answer', start.content.decode())
        self.assertNotIn('150 × 0.20', start.content.decode())
        submission = assessment.submissions.get()
        answers = {str(index): q['correct_answer']['answer'] for index, q in enumerate(submission.questions)}
        result = self.client.post(reverse('pages:recruiter-candidate-session', args=[submission.pk]), json.dumps({'answers': answers, 'revision':1, 'submit':True}), content_type='application/json', **self.host)
        self.assertEqual(result.json()['status'], 'submitted')
        submission.refresh_from_db()
        self.assertEqual(submission.score, 2)
        self.assertEqual([section['title'] for section in submission.section_scores], ['Arithmetic', 'Policy'])
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse('pages:recruiter-result', args=[submission.pk]), **self.host), 'Arithmetic')

    def test_nonstandard_headers_reordered_columns_and_second_sheet(self):
        rows = [['Recruiter question bank'], ['Right response', 'First choice', 'Prompt text', 'Second choice', 'Topic'], ['B', 'Red', 'Choose blue', 'Blue', 'Colour']]
        draft = self.upload(xlsx_upload([('Read me', [['Instructions']]), ('Bank', rows)]))
        map_url = reverse('pages:recruiter-import-map', args=[draft.pk])
        page = self.client.get(map_url, {'sheet':1, 'header_row':2}, **self.host)
        self.assertContains(page, 'Prompt text')
        self.map(draft, {'sheet':1, 'header_row':2, 'question':'2', 'option_a':'1', 'option_b':'3', 'answer':'0', 'subject':'4', 'answer_format':'letter'})
        self.assertEqual(draft.questions[0]['correct_answer']['answer'], 'Blue')
        self.assertEqual(draft.questions[0]['payload']['metadata']['source_row'], 3)
        self.assertEqual(self.publish(draft).status_code, 302)

    def test_invalid_rows_block_entire_publication(self):
        rows = [HEADERS, ROWS[1], ['No correct key', 'Yes', 'No', '', '', '', '', '']]
        draft = self.upload(csv_upload(rows))
        self.map(draft)
        self.assertTrue(draft.errors)
        self.assertEqual(draft.questions, [])
        response = self.publish(draft)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(RecruiterAssessment.objects.exists())
        self.assertContains(self.client.get(reverse('pages:recruiter-import-preview', args=[draft.pk]), **self.host), 'Row 3')

    def test_mapping_rejects_reused_and_out_of_range_columns(self):
        draft = self.upload()
        base = {**default_mapping(draft.sheets[0], 1), 'sheet':0, 'header_row':1}
        for change in ({'option_a':base['question']}, {'question':'999'}, {'sheet':99}, {'header_row':0}):
            response = self.client.post(reverse('pages:recruiter-import-map', args=[draft.pk]), {**base, **change}, **self.host)
            self.assertEqual(response.status_code, 400)
        draft.refresh_from_db()
        self.assertFalse(draft.questions)

    def test_import_ownership_and_expiration(self):
        draft = self.upload()
        self.map(draft)
        self.client.force_login(self.other)
        for name in ('recruiter-import-map', 'recruiter-import-preview'):
            url = reverse('pages:'+name, args=[draft.pk])
            self.assertEqual(self.client.get(url, **self.host).status_code, 404)
            self.assertEqual(self.client.post(url, self.settings, **self.host).status_code, 404)
        self.client.force_login(self.owner)
        draft.expires_at = timezone.now()-timedelta(seconds=1)
        draft.save(update_fields=['expires_at'])
        self.assertEqual(self.publish(draft).status_code, 404)
        self.assertFalse(RecruiterAssessment.objects.exists())
        self.upload(csv_upload())
        self.assertFalse(RecruiterQuestionImport.objects.filter(pk=draft.pk).exists())

    def test_students_cannot_upload_or_get_answer_key_previews(self):
        draft = self.upload()
        self.map(draft)
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(self.upload_url, {'workbook': csv_upload()}, **self.host).status_code, 302)
        self.assertEqual(self.client.get(reverse('pages:recruiter-import-preview', args=[draft.pk]), **self.host).status_code, 302)
        self.assertEqual(RecruiterQuestionImport.objects.count(), 1)

    def test_template_round_trips_and_upload_is_csrf_protected(self):
        template = self.client.get(reverse('pages:recruiter-import-template'), **self.host)
        self.assertEqual(template.status_code, 200)
        sheet = read_upload(SimpleUploadedFile('template.csv', template.content))[0]
        questions, errors = validate_questions(sheet, 1, default_mapping(sheet, 1))
        self.assertFalse(errors)
        self.assertEqual(len(questions), 2)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.owner)
        self.assertEqual(protected.post(self.upload_url, {'workbook':csv_upload()}, **self.host).status_code, 403)

    def test_workbook_text_is_escaped_and_preview_is_never_a_public_source(self):
        rows = [HEADERS, ['<script>bad()</script>', '<img src=x>', 'Safe', '', '', 'B', 'Subject', '<script>key()</script>']]
        draft = self.upload(csv_upload(rows))
        self.map(draft)
        page = self.client.get(reverse('pages:recruiter-import-preview', args=[draft.pk]), **self.host)
        self.assertContains(page, '&lt;script&gt;')
        self.assertNotContains(page, '<script>bad()</script>')
        self.assertIn('no-store', page.headers['Cache-Control'])
