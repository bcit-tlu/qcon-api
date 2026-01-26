# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .serializers import JsonToScormSerializer, DocxToJsonSerializer, ScormToJsonSerializer
from .pipelines.json_to_scorm import json_to_scorm, JsonToScormError
from .pipelines.scorm_to_json import scorm_to_json
from .pipelines.json_to_docx import json_to_docx, JsonToDocxError
from .pipelines.docx_to_json import docx_to_json, DocxToJsonError
from .pipelines.response_payload import build_status_payload
from rest_framework.views import APIView
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.parsers import JSONParser


from django.conf import settings

import logging
logger = logging.getLogger(__name__)
from .logging.contextfilter import QuestionlibraryFilenameFilter
loggingfilter = QuestionlibraryFilenameFilter()
logger.addFilter(loggingfilter)

class TokenAuthenticationWithBearer(TokenAuthentication):
    keyword = 'Bearer'

    def __init__(self):
        super(TokenAuthenticationWithBearer, self).__init__()

class DocxToJson(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthenticationWithBearer]
    serializer_class = DocxToJsonSerializer

    def post(self, request, format=None):
        is_random = False
        if 'randomize' in request.POST:
            if request.POST['randomize'].lower() in ("true", "yes"):
                is_random = True

        file_obj = request.data['temp_file']
        serializer = DocxToJsonSerializer(data={
            'temp_file': file_obj,
            'randomize': is_random
        })

        if not serializer.is_valid():
            error_payload = build_status_payload(
                "Error",
                "Validation failed",
                serializer.errors,
                questionlibrary=None,
                process=None,
            )
            return JsonResponse(error_payload, status=400)

        instance = serializer.save()

        try:
            json_data, question_library = docx_to_json(instance, logger)
            question_library.cleanup()
            return JsonResponse(json_data, status=200)
        except DocxToJsonError as exc:
            error_payload = build_status_payload(
                "Error",
                str(exc),
                "",
                process=exc.process,
                questionlibrary=instance,
            )
            instance.cleanup()
            return JsonResponse(error_payload, status=500)


class JsonToScorm(APIView):
    parser_classes = [JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthenticationWithBearer]
    serializer_class = JsonToScormSerializer

    def post(self, request, format=None):
        json_data = request.data
        try:
            file_response, ql_instance = json_to_scorm(json_data, logger)
            logger.addFilter(QuestionlibraryFilenameFilter(ql_instance))
            logger.info(f"[{ql_instance.id}] Transaction Finished")
            ql_instance.cleanup()
            return file_response
        except JsonToScormError as exc:
            error_payload = build_status_payload(
                "Error",
                "Validation failed",
                exc.errors,
                questionlibrary=None,
                process=None,
            )
            return JsonResponse(error_payload, status=400)


class ScormToJson(APIView):
    """
    Reverse API endpoint: Converts SCORM ZIP file to JSON (mirrors DocxToJson).
    This is step 1 of the reverse process: SCORM → JSON.
    """
    parser_classes = [MultiPartParser]
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthenticationWithBearer]
    serializer_class = ScormToJsonSerializer

    def post(self, request, format=None):
        file_obj = request.data.get('scorm_file')
        serializer = ScormToJsonSerializer(data={
            'scorm_file': file_obj
        })

        if not serializer.is_valid():
            error_payload = build_status_payload(
                "Error",
                "Validation failed",
                serializer.errors,
                questionlibrary=None,
                process=None,
            )
            return JsonResponse(error_payload, status=400)

        instance = serializer.save()
        logger.addFilter(QuestionlibraryFilenameFilter(instance))

        try:
            json_data, question_library = scorm_to_json(instance, logger)
            instance.cleanup()
            return JsonResponse(json_data, status=200)
        except Exception as e:
            logger.error(f"SCORM to JSON conversion failed: {str(e)}")
            error_payload = build_status_payload(
                "Error",
                str(e),
                "",
                questionlibrary=instance,
                process=None,
            )
            instance.cleanup()
            return JsonResponse(error_payload, status=500)


class JsonToDocx(APIView):
    """
    Reverse API endpoint: Converts JSON to DOCX (mirrors JsonToScorm).
    This is step 2 of the reverse process: JSON → DOCX.
    """
    parser_classes = [JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthenticationWithBearer]
    serializer_class = JsonToScormSerializer

    def post(self, request, format=None):
        json_data = request.data
        try:
            file_response, ql_instance = json_to_docx(json_data, logger)
        except JsonToDocxError as exc:
            error_payload = build_status_payload(
                "Error",
                "Validation failed",
                exc.errors,
                questionlibrary=None,
                process=None,
            )
            return JsonResponse(error_payload, status=400)
        except Exception as e:
            logger.error(f"JSON to DOCX conversion failed: {str(e)}")
            error_payload = build_status_payload(
                "Error",
                str(e),
                "",
                questionlibrary=None,
                process=None,
            )
            return JsonResponse(error_payload, status=500)

        ql_instance.cleanup()

        return file_response


class RootPath(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        from .models import StatusResponse
        from .serializers import StatusResponseSerializer

        status = StatusResponse(version_number=settings.APP_VERSION)
        serializer = StatusResponseSerializer(status)

        return JsonResponse(serializer.data,
                            json_dumps_params={'indent': 2},
                            status=200)


from django.shortcuts import redirect


def view_404(request, exception=None):
    return redirect('/')


def redirect_view(request, namespace, name, slug, actualurl):
    print(slug)
    print(actualurl)
    return redirect('/' + actualurl)
    # return None


def redirect_root(request, namespace, name, slug):
    print(slug)
    return redirect('/')
