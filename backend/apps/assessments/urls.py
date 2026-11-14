from django.urls import path

from .learning_views import WorkshopStartView, WorkshopSessionView, ItemEventView, WorkshopReviewInviteView

from .views import (
    AdaptiveAdvanceView,
    AttemptEndView,
    AttemptProgressSaveView,
    AttemptStartView,
    FullTestQuestionView,
    FullTestSectionSubmitView,
    FullTestSectionView,
    FullTestSubmitView,
    PracticeProgressUpdateView,
    SectionCatalogView,
    SectionTestSubmitView,
)

urlpatterns = [
    path("workshops/<int:session_id>/review-invite/", WorkshopReviewInviteView.as_view(), name="workshop-review-invite"),
    path("workshops/start/", WorkshopStartView.as_view(), name="workshop-start"),
    path("workshops/<int:session_id>/", WorkshopSessionView.as_view(), name="workshop-session"),
    path("item-events/", ItemEventView.as_view(), name="item-event"),
    path("adaptive/<int:attempt_id>/next/", AdaptiveAdvanceView.as_view(), name="adaptive-advance"),
    path("sections/", SectionCatalogView.as_view(), name="sections"),
    path("attempts/start/", AttemptStartView.as_view(), name="attempt-start"),
    path("attempts/<int:attempt_id>/end/", AttemptEndView.as_view(), name="attempt-end"),
    path("attempts/<int:attempt_id>/progress/", AttemptProgressSaveView.as_view(), name="attempt-progress"),
    path("practice-progress/", PracticeProgressUpdateView.as_view(), name="practice-progress"),
    path("section-tests/<int:attempt_id>/submit/", SectionTestSubmitView.as_view(), name="section-test-submit"),
    path("full-tests/<int:attempt_id>/question/", FullTestQuestionView.as_view(), name="full-test-question"),
    path("full-tests/<int:attempt_id>/section/", FullTestSectionView.as_view(), name="full-test-section"),
    path("full-tests/<int:attempt_id>/section-submit/", FullTestSectionSubmitView.as_view(), name="full-test-section-submit"),
    path("full-tests/<int:attempt_id>/submit/", FullTestSubmitView.as_view(), name="full-test-submit"),
]
