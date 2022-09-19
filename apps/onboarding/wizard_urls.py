from django.urls import path
from apps.onboarding import wizard_views
'''If you made any changes in url names here,
change at update_wizard_steps function. '''

wizard_url_patterns1 = [
    path('',          wizard_views.WizardView.as_view(),  name='wizard_view'),
    path('wizard_del/',       wizard_views.WizardDelete.as_view(),  name='wizard_delete'),

    path('buform/', wizard_views.WizardBt.as_view(), name='wiz_bu_form'),
    path('buform/<str:pk>/', wizard_views.WizardBt.as_view(), name='wiz_bu_update'),
    path('buform/del/<str:pk>/', wizard_views.WizardBt.as_view(), name='wiz_bu_delete'),

    path('shiftform/', wizard_views.WizardShift.as_view(), name='wiz_shift_form'),
    path('shiftform/<str:pk>/', wizard_views.WizardShift.as_view(), name='wiz_shift_update'),
    path('shiftform/del/<str:pk>/', wizard_views.WizardShift.as_view(), name='wiz_shift_delete'),

    path('preview', wizard_views.WizardPreview.as_view(), name='wizard_preview'),
    path('saveWizard', wizard_views.save_wizard, name='saveWizard'),
    path('save_as_draft/', wizard_views.save_as_draft, name='save_asdraft'),
    path('delete-draft/', wizard_views.delete_from_draft, name='delete_from_draft'),
]

wizard_url_patterns2  = [
    path('peoplform/', wizard_views.WizardPeople.as_view(), name='wiz_people_form'),
    path('peoplform/<str:pk>/', wizard_views.WizardPeople.as_view(), name='wiz_people_update'),
    path('peoplform/del/<str:pk>/', wizard_views.WizardPeople.as_view(), name='wiz_people_delete'),

    path('pgroupform/', wizard_views.WizardPgroup.as_view(), name='wiz_pgroup_form'),
    path('pgroupform/<str:pk>/', wizard_views.WizardPgroup.as_view(), name='wiz_pgroup_update'),
    path('pgroupform/del/<str:pk>/', wizard_views.WizardPgroup.as_view(), name='wiz_pgroup_delete'),
]

