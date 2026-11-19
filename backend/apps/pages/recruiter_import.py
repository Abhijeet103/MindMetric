"""Recruiter-owned upload, column mapping, preview and explicit publication."""

import csv
import io
from datetime import timedelta

from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from .models import RecruiterAssessment, RecruiterQuestionImport
from .question_import import (FIELD_LABELS, MAPPING_FIELDS, ImportProblem, default_mapping, read_upload, validate_questions)
from .recruiter import RecruiterAssessmentForm, RecruiterOnlyMixin, RequiresCreditsMixin, current_tenant


class QuestionUploadForm(forms.Form):
    workbook = forms.FileField(label="Question spreadsheet", widget=forms.ClearableFileInput(attrs={"accept": ".xlsx,.xlsm,.xls,.csv"}), help_text="Excel or UTF-8 CSV, up to 2 MB. You can select a worksheet and map your own column names next.")


class ColumnMappingForm(forms.Form):
    sheet = forms.TypedChoiceField(coerce=int, label="Worksheet")
    header_row = forms.IntegerField(min_value=1, max_value=20, initial=1, label="Header row")
    answer_format = forms.ChoiceField(choices=[("auto", "Detect automatically (ambiguous values are flagged)"), ("letter", "Option letters: A, B, C…"), ("number", "Option numbers: 1, 2, 3…"), ("text", "Exact option text")], initial="auto", label="Correct-answer format")

    def __init__(self, *args, sheets, sheet_index, header_row, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sheet"].choices = [(index, sheet["name"]) for index, sheet in enumerate(sheets)]
        rows = sheets[sheet_index]["rows"]
        headers = rows[header_row-1] if len(rows) >= header_row else []
        column_count = max((len(row) for row in rows), default=0)
        columns = [(str(index), f"Column {index+1}: {headers[index][:80] if index < len(headers) and headers[index] else '(no header)'}") for index in range(column_count)]
        for field in MAPPING_FIELDS:
            required = field in {"question", "option_a", "option_b", "answer"}
            self.fields[field] = forms.ChoiceField(choices=[("", "Choose a column" if required else "Not used"), *columns], required=required, label=FIELD_LABELS[field])
        self.order_fields(["sheet", "header_row", "question", *[f"option_{letter}" for letter in "abcdef"], "answer", "answer_format", "subject", "explanation"])

    def clean(self):
        data = super().clean()
        columns = [data[field] for field in MAPPING_FIELDS if data.get(field) not in (None, "")]
        if len(set(columns)) != len(columns):
            raise forms.ValidationError("Map each column to only one field. Question, options and answer must use different columns.")
        return data


class CustomAssessmentSettingsForm(RecruiterAssessmentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("modules", "difficulty", "questions_per_module"):
            self.fields.pop(name)


def owned_import(request, import_id, lock=False):
    query = RecruiterQuestionImport.objects.select_for_update() if lock else RecruiterQuestionImport.objects
    return get_object_or_404(query, pk=import_id, recruiter=request.user, tenant=current_tenant(request), expires_at__gt=timezone.now())


def selected_layout(draft, data):
    try:
        sheet_index = int(data.get("sheet", draft.mapping.get("sheet", 0)))
        header_row = int(data.get("header_row", draft.mapping.get("header_row", 1)))
    except (TypeError, ValueError):
        return 0, 1
    return (sheet_index if 0 <= sheet_index < len(draft.sheets) else 0, header_row if 1 <= header_row <= 20 else 1)


def mapping_context(draft, form, sheet_index, header_row):
    sheet = draft.sheets[sheet_index]
    return {"page_title": "Map spreadsheet columns | MindMetric", "draft": draft, "form": form,
        "sample_rows": sheet["rows"][header_row-1:header_row+4], "sheet_index": sheet_index, "header_row": header_row}


@method_decorator(never_cache, name="dispatch")
class RecruiterQuestionUploadView(RecruiterOnlyMixin, RequiresCreditsMixin, View):
    def get(self, request):
        return render(request, "pages/recruiter/upload.html", {"page_title": "Upload custom assessment | MindMetric", "form": QuestionUploadForm()})

    def post(self, request):
        form = QuestionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                sheets = read_upload(form.cleaned_data["workbook"])
            except ImportProblem as exc:
                form.add_error("workbook", str(exc))
            else:
                tenant = current_tenant(request)
                RecruiterQuestionImport.objects.filter(recruiter=request.user, tenant=tenant, expires_at__lte=timezone.now()).delete()
                draft = RecruiterQuestionImport.objects.create(tenant=tenant, recruiter=request.user, filename=form.cleaned_data["workbook"].name[:255], sheets=sheets, expires_at=timezone.now()+timedelta(hours=1))
                return redirect("pages:recruiter-import-map", import_id=draft.pk)
        return render(request, "pages/recruiter/upload.html", {"page_title": "Upload custom assessment | MindMetric", "form": form}, status=400)


@method_decorator(never_cache, name="dispatch")
class RecruiterColumnMappingView(RecruiterOnlyMixin, View):
    def get(self, request, import_id):
        draft = owned_import(request, import_id)
        if draft.assessment_id:
            return redirect("pages:recruiter-assessment", assessment_id=draft.assessment_id)
        sheet_index, header_row = selected_layout(draft, request.GET)
        initial = {**default_mapping(draft.sheets[sheet_index], header_row), "sheet": sheet_index, "header_row": header_row}
        if not request.GET and draft.mapping:
            initial.update(draft.mapping)
        form = ColumnMappingForm(sheets=draft.sheets, sheet_index=sheet_index, header_row=header_row, initial=initial)
        return render(request, "pages/recruiter/import_map.html", mapping_context(draft, form, sheet_index, header_row))

    def post(self, request, import_id):
        draft = owned_import(request, import_id)
        if draft.assessment_id:
            return redirect("pages:recruiter-assessment", assessment_id=draft.assessment_id)
        sheet_index, header_row = selected_layout(draft, request.POST)
        form = ColumnMappingForm(request.POST, sheets=draft.sheets, sheet_index=sheet_index, header_row=header_row)
        if form.is_valid():
            questions, errors = validate_questions(draft.sheets[form.cleaned_data["sheet"]], form.cleaned_data["header_row"], form.cleaned_data)
            draft.mapping, draft.questions, draft.errors = form.cleaned_data, questions if not errors else [], errors
            draft.save(update_fields=["mapping", "questions", "errors"])
            return redirect("pages:recruiter-import-preview", import_id=draft.pk)
        return render(request, "pages/recruiter/import_map.html", mapping_context(draft, form, sheet_index, header_row), status=400)


@method_decorator(never_cache, name="dispatch")
class RecruiterImportPreviewView(RecruiterOnlyMixin, RequiresCreditsMixin, View):
    def context(self, request, draft, form):
        return {"page_title": "Review custom assessment | MindMetric", "draft": draft, "form": form, "error_count": len(draft.errors), "row_errors": draft.errors[:60],
            "preview_questions": [{"row": item["payload"]["metadata"]["source_row"], "subject": item["payload"]["metadata"]["subject"], "text": item["payload"]["prompt"]["question"], "options": item["payload"]["options"], "answer": item["correct_answer"]["answer"], "explanation": item["payload"]["prompt"]["explanation"]} for item in draft.questions]}

    def get(self, request, import_id):
        draft = owned_import(request, import_id)
        if draft.assessment_id:
            return redirect("pages:recruiter-assessment", assessment_id=draft.assessment_id)
        form = CustomAssessmentSettingsForm(tenant=current_tenant(request), initial={"organization": request.user.organization})
        return render(request, "pages/recruiter/import_preview.html", self.context(request, draft, form))

    def post(self, request, import_id):
        form = CustomAssessmentSettingsForm(request.POST, tenant=current_tenant(request))
        with transaction.atomic():
            draft = owned_import(request, import_id, lock=True)
            if draft.assessment_id:
                return redirect("pages:recruiter-assessment", assessment_id=draft.assessment_id)
            if not draft.questions or draft.errors:
                form.add_error(None, "Resolve all import errors before creating the assessment.")
            elif form.is_valid():
                values = dict(form.cleaned_data)
                days = values.pop("open_days")
                assessment = RecruiterAssessment.objects.create(tenant=draft.tenant, recruiter=request.user, custom_questions=draft.questions, modules=[],
                    closes_at=timezone.now()+timedelta(days=days), **values)
                draft.assessment = assessment
                # Discard unrelated workbook cells after explicit publication.
                draft.sheets = []
                draft.save(update_fields=["assessment", "sheets"])
                messages.success(request, "Custom assessment created from your spreadsheet. Copy the link to share it with students.")
                return redirect("pages:recruiter-assessment", assessment_id=assessment.pk)
        return render(request, "pages/recruiter/import_preview.html", self.context(request, draft, form), status=400)


@method_decorator(never_cache, name="dispatch")
class RecruiterImportTemplateView(RecruiterOnlyMixin, View):
    def get(self, request):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Question", "Option A", "Option B", "Option C", "Option D", "Correct answer", "Subject", "Explanation"])
        writer.writerow(["What is 20% of 150?", "20", "25", "30", "35", "C", "Arithmetic", "150 multiplied by 0.20 equals 30."])
        writer.writerow(["The policy says every invoice needs approval. An invoice can be paid without approval.", "True", "False", "", "", "B", "Verbal reasoning", "The statement contradicts the policy."])
        response = HttpResponse("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="mindmetric-question-template.csv"'
        return response
