from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import (
    api_view,
)
from rest_framework.response import Response

from apps.common.models import PrivacyPolicy, TermsConditions
from apps.common.serializers import (
    PrivacyPolicySerializer,
    TermsConditionsSerializer,
)


@swagger_auto_schema(method="get", tags=["common"])
@api_view(["GET"])
def get_privacy_policy(request):
    policy = PrivacyPolicy.objects.first()
    serializer = PrivacyPolicySerializer(policy)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="patch", request_body=PrivacyPolicySerializer, tags=["Cores"]
)
@api_view(["PATCH"])
def create_or_update_privacy_policy(request):
    policy = PrivacyPolicy.objects.first()
    serializer = PrivacyPolicySerializer(policy, data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="get", tags=["Cores"])
@api_view(["GET"])
def get_terms_conditions(request):
    terms = TermsConditions.objects.first()
    serializer = TermsConditionsSerializer(terms)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="patch", request_body=TermsConditionsSerializer, tags=["Cores"]
)
@api_view(["PATCH"])
def create_or_update_terms_conditions(request):
    terms = TermsConditions.objects.first()

    serializer = TermsConditionsSerializer(terms, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(
        {"error": "Invalid data. Please check your input."},
        status=status.HTTP_400_BAD_REQUEST,
    )
