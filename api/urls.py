# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import include, path, re_path
from . import views
from django.conf import settings

urlpatterns = [
    path('docx-to-json', views.DocxToJson.as_view(), name='DocxToJson'),
    path('json-to-scorm', views.JsonToScorm.as_view(), name='JsonToScorm'),
    path('scorm-to-json', views.ScormToJson.as_view(), name='ScormToJson'),
    path('json-to-docx', views.JsonToDocx.as_view(), name='JsonToDocx'),
]
