from backend.apps.assessments.learning_views import WorkshopPageView, WorkshopPeerReviewView
from django.urls import path

from .recruiter import (
    RecruiterDashboardView, RecruiterCreateView, RecruiterAssessmentView, RecruiterResultView,
    RecruiterInviteView, RecruiterCandidateStartView, RecruiterCandidateSessionView,
)
from .recruiter_import import (
    RecruiterQuestionUploadView, RecruiterColumnMappingView, RecruiterImportPreviewView, RecruiterImportTemplateView,
)
from .results import AttemptResultsView
from .student import (
    ApplicationDeadlineCreateView,
    ApplicationDeadlineDeleteView,
    CompanyLookupView,
    HiringResearchStartView,
    HiringResearchStatusView,
    LegalPageView,
)

from .views import (
    AdaptiveTestPageView,
    AssessmentGuidePageView,
    AssessmentPracticePageView,
    ContactInquiryCreateView,
    DashboardPageView,
    FullTestPageView,
    HomePageView,
    LoginPageView,
    ModuleGuidePageView,
    PracticePageView,
    PricingPageView,
    PortalFeedbackCreateView,
    SectionDetailPageView,
    SectionsPageView,
    SectionTestSetupView,
    SubscriptionPageView,
    TestSuggestionCreateView,
    TrackWaitlistCreateView,
)

app_name = "pages"

urlpatterns = [
    path("recruiter/upload/", RecruiterQuestionUploadView.as_view(), name="recruiter-upload"),
    path("recruiter/upload/template/", RecruiterImportTemplateView.as_view(), name="recruiter-import-template"),
    path("recruiter/upload/<uuid:import_id>/map/", RecruiterColumnMappingView.as_view(), name="recruiter-import-map"),
    path("recruiter/upload/<uuid:import_id>/preview/", RecruiterImportPreviewView.as_view(), name="recruiter-import-preview"),
    path("recruiter/", RecruiterDashboardView.as_view(), name="recruiter-dashboard"),
    path("recruiter/create/", RecruiterCreateView.as_view(), name="recruiter-create"),
    path("recruiter/assessments/<uuid:assessment_id>/", RecruiterAssessmentView.as_view(), name="recruiter-assessment"),
    path("recruiter/results/<uuid:submission_id>/", RecruiterResultView.as_view(), name="recruiter-result"),
    path("assess/<uuid:token>/", RecruiterInviteView.as_view(), name="recruiter-invite"),
    path("assess/<uuid:token>/start/", RecruiterCandidateStartView.as_view(), name="recruiter-candidate-start"),
    path("assess/session/<uuid:submission_id>/", RecruiterCandidateSessionView.as_view(), name="recruiter-candidate-session"),
    path("practice/peer-review/<str:token>/", WorkshopPeerReviewView.as_view(), name="workshop-peer-review"),
    path("practice/<slug:assessment_slug>/workshop/", WorkshopPageView.as_view(), name="assessment-workshop"),
    path("", HomePageView.as_view(), name="home"),
    path("pricing/", PricingPageView.as_view(), name="pricing"),
    path("contact-sales/", ContactInquiryCreateView.as_view(), name="contact-sales"),
    path("suggest-test/", TestSuggestionCreateView.as_view(), name="suggest-test"),
    path("track-waitlist/", TrackWaitlistCreateView.as_view(), name="track-waitlist"),
    path("practice/", PracticePageView.as_view(), name="practice"),
    path("practice/adaptive/<int:attempt_id>/", AdaptiveTestPageView.as_view(), name="adaptive-test"),
    path("guides/<slug:assessment_guide_slug>/", AssessmentGuidePageView.as_view(), name="assessment-guide"),
    path(
        "guides/<slug:assessment_guide_slug>/<slug:module_guide_slug>/",
        ModuleGuidePageView.as_view(),
        name="module-guide",
    ),
    path("practice/<slug:assessment_slug>/", AssessmentPracticePageView.as_view(), name="assessment-practice"),
    path("practice/<slug:assessment_slug>/full-test/", FullTestPageView.as_view(), name="assessment-full-test"),
    path("practice/<slug:assessment_slug>/modules/<slug:slug>/", SectionDetailPageView.as_view(), name="assessment-section-detail"),
    path("practice/<slug:assessment_slug>/modules/<slug:slug>/test-setup/", SectionTestSetupView.as_view(), name="assessment-section-test-setup"),
    path("full-test/", FullTestPageView.as_view(), {"assessment_slug": "prepgia"}, name="full-test"),
    path("subscription/", SubscriptionPageView.as_view(), name="subscription"),
    path("sections/", SectionsPageView.as_view(), name="sections"),
    path("sections/<slug:slug>/", SectionDetailPageView.as_view(), {"assessment_slug": "prepgia"}, name="section-detail"),
    path("login/", LoginPageView.as_view(), name="login"),
    path("dashboard/", DashboardPageView.as_view(), name="dashboard"),
    path("results/<int:attempt_id>/", AttemptResultsView.as_view(), name="attempt-results"),
    path("applications/add/", ApplicationDeadlineCreateView.as_view(), name="application-add"),
    path("applications/<int:deadline_id>/delete/", ApplicationDeadlineDeleteView.as_view(), name="application-delete"),
    path("companies/", CompanyLookupView.as_view(), name="company-lookup"),
    path("companies/research/", HiringResearchStartView.as_view(), name="hiring-research-start"),
    path("companies/research/<uuid:report_id>/", HiringResearchStatusView.as_view(), name="hiring-research-status"),
    path("legal/<slug:slug>/", LegalPageView.as_view(), name="legal-page"),
    path("feedback/", PortalFeedbackCreateView.as_view(), name="feedback"),
]
